"""
Analytics router for project metrics and productivity data.
Refactored for Async operations with proper Dependency Injection.
"""

import json
import uuid
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from async_dependencies import require_project_member
from database import get_async_db
from dependencies.services import (
    get_analytics_service,
    get_project_service,
    get_task_history_service,
)
from models.project import Project
from models.user import User
from routers.auth import get_current_active_user
from schemas.analytics import (
    AnalyticsOverviewResponse,
    BatchActivityRequest,
    BatchActivityResponse,
    TeamWorkloadPaginatedResponse,
)
from services.async_analytics_service import AsyncAnalyticsService
from services.async_project_service import AsyncProjectService
from services.async_task_history_service import AsyncTaskHistoryService
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


def _format_activity(
    activity: Any, user_map: dict, project_name: str = "", project_id: str = ""
) -> dict[str, Any]:
    """Helper to format a single activity."""
    user = user_map.get(activity.user_id)
    user_name = user.name if user else f"User {activity.user_id}"

    formatted = {
        "id": str(activity.id),
        "type": activity.activity_type.value,
        "user_name": user_name,
        "task_title": activity.task_title,
        "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,
        "description": activity.description,
        "project_name": project_name,
        "project_id": project_id or str(activity.project_id),
    }

    if activity.new_values:
        try:
            new_values = json.loads(activity.new_values)
            if "assignee_name" in new_values:
                formatted["assignee_name"] = new_values["assignee_name"]
        except (json.JSONDecodeError, TypeError):
            pass

    return formatted


async def _get_user_map(db: AsyncSession, user_ids: set) -> dict:
    """Helper to batch fetch users."""
    if not user_ids:
        return {}
    users_result = await db.execute(select(User).filter(User.id.in_(user_ids)))
    users = users_result.scalars().all()
    return {u.id: u for u in users}


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    analytics_service: AsyncAnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get global analytics overview for the current user across all projects."""
    return await analytics_service.get_analytics_overview(current_user.id, period=period)


@router.get("/team-workload", response_model=TeamWorkloadPaginatedResponse)
async def get_team_workload(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str = Query(None, description="Search term for user names"),
    sort_by: str = Query("tasks", description="Sort by: 'tasks' or 'name'"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    analytics_service: AsyncAnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get paginated team workload data."""
    return await analytics_service.get_team_workload_paginated(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/projects/{project_id}/dashboard")
async def get_dashboard_metrics(
    project_id: str,
    analytics_service: AsyncAnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
    project: Project = Depends(require_project_member),
) -> dict[str, Any]:
    """Get dashboard metrics for a project."""
    return await analytics_service.get_project_analytics(project.id)


@router.get("/projects/{project_id}/productivity")
async def get_productivity_data(
    project_id: str,
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
    group_by: str = Query("week", description="Group by: day, week, month"),
    analytics_service: AsyncAnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
    project: Project = Depends(require_project_member),
) -> dict[str, Any]:
    """Get productivity data for a project."""
    return await analytics_service.get_project_productivity(
        project.id, period=period, group_by=group_by
    )


@router.get("/projects/{project_id}/contributions")
async def get_contributions(
    project_id: str,
    analytics_service: AsyncAnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
    project: Project = Depends(require_project_member),
) -> dict[str, Any]:
    """Get team contributions for a project."""
    return await analytics_service.get_project_contributions(project.id)


@router.get("/projects/{project_id}/activity", response_model=dict[str, Any])
async def get_recent_activity(
    project_id: str,
    limit: int = Query(10, description="Number of activities to return"),
    db: AsyncSession = Depends(get_async_db),
    task_history_service: AsyncTaskHistoryService = Depends(get_task_history_service),
    current_user: User = Depends(get_current_active_user),
    project: Project = Depends(require_project_member),
) -> dict[str, Any]:
    """Get recent activity for a project."""
    activities = await task_history_service.get_recent_activities(project.id, limit)

    user_ids = {activity.user_id for activity in activities}
    user_map = await _get_user_map(db, user_ids)

    formatted_activities = [
        _format_activity(activity, user_map, project.name, str(project.id))
        for activity in activities
    ]

    return {"activities": formatted_activities, "total_count": len(formatted_activities)}


@router.get("/activity", response_model=dict[str, Any])
async def get_all_recent_activity(
    limit: int = Query(20, description="Number of activities to return"),
    db: AsyncSession = Depends(get_async_db),
    project_service: AsyncProjectService = Depends(get_project_service),
    task_history_service: AsyncTaskHistoryService = Depends(get_task_history_service),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Get recent activity across all projects the user has access to."""

    user_projects = await project_service.get_projects(user_id=uuid.UUID(str(current_user.id)))
    project_ids = [p.id for p in user_projects]

    if not project_ids:
        return {"activities": [], "total_count": 0}

    activities = await task_history_service.get_recent_activities_for_projects(project_ids, limit)

    user_ids = {activity.user_id for activity in activities}
    user_map = await _get_user_map(db, user_ids)
    project_map = {p.id: p for p in user_projects}

    formatted_activities = []
    for activity in activities:
        project = project_map.get(activity.project_id)
        project_name = project.name if project else "Unknown Project"
        formatted_activities.append(
            _format_activity(
                activity,
                user_map,
                project_name,
                str(activity.project_id),
            )
        )

    return {"activities": formatted_activities, "total_count": len(formatted_activities)}


@router.post("/activity/batch", response_model=list[BatchActivityResponse])
async def get_batch_recent_activity(
    request: BatchActivityRequest,
    db: AsyncSession = Depends(get_async_db),
    project_service: AsyncProjectService = Depends(get_project_service),
    task_history_service: AsyncTaskHistoryService = Depends(get_task_history_service),
    current_user: User = Depends(get_current_active_user),
) -> list[Any]:
    """Get recent activity for multiple projects in batch."""
    project_ids_str = request.project_ids
    limit = request.limit

    if not project_ids_str:
        return []

    # Validate UUIDs
    valid_project_uuids: list[uuid.UUID] = []
    results_map: dict[str, dict[str, Any]] = {}

    for pid in project_ids_str:
        try:
            valid_project_uuids.append(uuid.UUID(pid))
        except ValueError:
            results_map[pid] = {"projectId": pid, "error": "Invalid project ID format"}

    if not valid_project_uuids:
        return list(results_map.values())

    # Check permissions
    user_projects = await project_service.get_projects(user_id=uuid.UUID(str(current_user.id)))
    accessible_project_ids = {p.id for p in user_projects}

    accessible_requested_uuids: list[uuid.UUID] = []
    for pid_uuid in valid_project_uuids:
        if pid_uuid in accessible_project_ids:
            accessible_requested_uuids.append(pid_uuid)
        else:
            results_map[str(pid)] = {
                "projectId": str(pid),
                "error": "Project not found or access denied",
            }

    if not accessible_requested_uuids:
        return list(results_map.values())

    # Batch fetch activities
    limit_int = limit if limit is not None else 10
    total_limit = limit_int * len(accessible_requested_uuids) * 2
    activities = await task_history_service.get_recent_activities_for_projects(
        accessible_requested_uuids, limit=total_limit
    )

    # Group by project
    activities_by_project: dict[str, list[Any]] = defaultdict(list)
    user_ids_to_fetch: set[Any] = set()

    for activity in activities:
        pid_str = str(activity.project_id)
        if len(activities_by_project[pid_str]) < limit_int:
            activities_by_project[pid_str].append(activity)
            user_ids_to_fetch.add(activity.user_id)

    user_map = await _get_user_map(db, user_ids_to_fetch)

    # Format results
    for pid_uuid in accessible_requested_uuids:
        pid_str = str(pid_uuid)
        if pid_str in results_map:
            continue

        project_activities = activities_by_project.get(pid_str, [])
        project_name = next((p.name for p in user_projects if p.id == pid), "")

        formatted_activities = [
            _format_activity(activity, user_map, project_name, pid_str)
            for activity in project_activities
        ]

        results_map[pid_str] = {"projectId": pid_str, "activities": formatted_activities}

    return [results_map[pid_str] for pid_str in project_ids_str if pid_str in results_map]
