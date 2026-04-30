"""Analytics router for active frontend metrics."""

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
    activity: Any, user_map: dict[Any, User], project_name: str = "", project_id: str = ""
) -> dict[str, Any]:
    """Format task history activity for legacy analytics activity endpoints."""
    user = user_map.get(activity.user_id)
    activity_type = (
        activity.activity_type.value
        if hasattr(activity.activity_type, "value")
        else str(activity.activity_type)
    )
    formatted = {
        "id": str(activity.id),
        "type": activity_type,
        "user_name": user.name if user else f"User {activity.user_id}",
        "task_title": getattr(activity, "task_title", None),
        "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,
        "description": getattr(activity, "description", None),
        "project_name": project_name,
        "project_id": project_id or str(activity.project_id),
    }

    new_values = getattr(activity, "new_values", None)
    if new_values:
        try:
            parsed_values = json.loads(new_values)
            if isinstance(parsed_values, dict) and "assignee_name" in parsed_values:
                formatted["assignee_name"] = parsed_values["assignee_name"]
        except (json.JSONDecodeError, TypeError):
            pass

    return formatted


async def _get_user_map(db: AsyncSession, user_ids: set[Any]) -> dict[Any, User]:
    """Batch fetch users by ID for activity formatting."""
    if not user_ids:
        return {}
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = users_result.scalars().all()
    return {user.id: user for user in users}


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
    """Get dashboard metrics for a project. Kept for API compatibility."""
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
    """Get productivity data for a project. Kept for API compatibility."""
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
    """Get team contributions for a project. Kept for API compatibility."""
    return await analytics_service.get_project_contributions(project.id)


@router.get("/projects/{project_id}/activity", response_model=dict[str, Any])
async def get_recent_activity(
    project_id: str,
    limit: int = Query(10, ge=1, le=100, description="Number of activities to return"),
    db: AsyncSession = Depends(get_async_db),
    task_history_service: AsyncTaskHistoryService = Depends(get_task_history_service),
    current_user: User = Depends(get_current_active_user),
    project: Project = Depends(require_project_member),
) -> dict[str, Any]:
    """Get recent activity for a project. Kept for API compatibility."""
    activities = await task_history_service.get_recent_activities(project.id, limit)
    user_map = await _get_user_map(db, {activity.user_id for activity in activities})
    formatted_activities = [
        _format_activity(activity, user_map, project.name, str(project.id))
        for activity in activities
    ]
    return {"activities": formatted_activities, "total_count": len(formatted_activities)}


@router.get("/activity", response_model=dict[str, Any])
async def get_all_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Number of activities to return"),
    db: AsyncSession = Depends(get_async_db),
    project_service: AsyncProjectService = Depends(get_project_service),
    task_history_service: AsyncTaskHistoryService = Depends(get_task_history_service),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Get recent activity across accessible projects. Kept for API compatibility."""
    user_projects = await project_service.get_projects(user_id=uuid.UUID(str(current_user.id)))
    project_ids = [project.id for project in user_projects]

    if not project_ids:
        return {"activities": [], "total_count": 0}

    activities = await task_history_service.get_recent_activities_for_projects(project_ids, limit)
    user_map = await _get_user_map(db, {activity.user_id for activity in activities})
    project_map = {project.id: project for project in user_projects}

    formatted_activities = [
        _format_activity(
            activity,
            user_map,
            project.name
            if (project := project_map.get(activity.project_id)) is not None
            else "Unknown Project",
            str(activity.project_id),
        )
        for activity in activities
    ]
    return {"activities": formatted_activities, "total_count": len(formatted_activities)}


@router.post("/activity/batch", response_model=list[BatchActivityResponse])
async def get_batch_recent_activity(
    request: BatchActivityRequest,
    db: AsyncSession = Depends(get_async_db),
    project_service: AsyncProjectService = Depends(get_project_service),
    task_history_service: AsyncTaskHistoryService = Depends(get_task_history_service),
    current_user: User = Depends(get_current_active_user),
) -> list[dict[str, Any]]:
    """Get recent activity for multiple projects in batch. Kept for API compatibility."""
    project_ids_str = request.project_ids
    limit = request.limit or 10
    results_map: dict[str, dict[str, Any]] = {}
    valid_project_uuids: list[uuid.UUID] = []

    for project_id_str in project_ids_str:
        try:
            valid_project_uuids.append(uuid.UUID(project_id_str))
        except ValueError:
            results_map[project_id_str] = {
                "projectId": project_id_str,
                "error": "Invalid project ID format",
            }

    if valid_project_uuids:
        user_projects = await project_service.get_projects(user_id=uuid.UUID(str(current_user.id)))
        project_map = {project.id: project for project in user_projects}
        accessible_project_ids = set(project_map)
        accessible_requested_uuids = [
            project_id for project_id in valid_project_uuids if project_id in accessible_project_ids
        ]

        for project_id in valid_project_uuids:
            if project_id not in accessible_project_ids:
                results_map[str(project_id)] = {
                    "projectId": str(project_id),
                    "error": "Project not found or access denied",
                }

        if accessible_requested_uuids:
            total_limit = limit * len(accessible_requested_uuids) * 2
            activities = await task_history_service.get_recent_activities_for_projects(
                accessible_requested_uuids, limit=total_limit
            )
            activities_by_project: dict[str, list[Any]] = defaultdict(list)
            user_ids_to_fetch: set[Any] = set()

            for activity in activities:
                project_id_str = str(activity.project_id)
                if len(activities_by_project[project_id_str]) < limit:
                    activities_by_project[project_id_str].append(activity)
                    user_ids_to_fetch.add(activity.user_id)

            user_map = await _get_user_map(db, user_ids_to_fetch)

            for project_id in accessible_requested_uuids:
                project_id_str = str(project_id)
                project = project_map[project_id]
                formatted_activities = [
                    _format_activity(activity, user_map, project.name, project_id_str)
                    for activity in activities_by_project.get(project_id_str, [])
                ]
                results_map[project_id_str] = {
                    "projectId": project_id_str,
                    "activities": formatted_activities,
                }

    return [
        results_map[project_id_str]
        for project_id_str in project_ids_str
        if project_id_str in results_map
    ]
