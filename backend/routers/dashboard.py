"""
Dashboard router for overview analytics and statistics.
Refactored for Async operations with proper Dependency Injection.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from dependencies.services import get_dashboard_service
from models.user import User
from routers.auth import get_current_active_user
from schemas.dashboard import (
    ActivityProjectResponse,
    ActivityUserResponse,
    DashboardActivityResponse,
    DashboardOverviewResponse,
    DashboardProjectResponse,
    DashboardStatsResponse,
)
from services.async_dashboard_service import AsyncDashboardService
from utils.logger import setup_logger

logger = setup_logger("dashboard_router")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _build_activity_response(activity: dict) -> DashboardActivityResponse:
    """Helper to build activity response from dict."""
    project_info = activity.get("project")
    project_response = None

    if isinstance(project_info, dict):
        project_response = ActivityProjectResponse(
            id=project_info.get("id"), name=project_info.get("name", "Unknown Project")
        )
    elif isinstance(project_info, str):
        project_response = ActivityProjectResponse(name=project_info)

    user_info = activity.get("user", {})
    user_response = ActivityUserResponse(
        id=user_info.get("id", ""),
        name=user_info.get("name", "Unknown User"),
        avatar=user_info.get("avatar"),
    )

    return DashboardActivityResponse(
        id=activity.get("id", ""),
        user=user_response,
        action=activity.get("action", ""),
        target=activity.get("target"),
        time=activity.get("time"),
        project=project_response,
    )


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    dashboard_service: AsyncDashboardService = Depends(get_dashboard_service),
    current_user: User = Depends(get_current_active_user),
) -> DashboardOverviewResponse:
    """
    Get dashboard overview with statistics and recent activities.
    Uses async database operations for better performance.
    """
    try:
        stats_data = await dashboard_service.get_overview_stats(current_user.id)
        recent_projects_data = await dashboard_service.get_recent_projects(current_user.id, limit=5)
        activities_data = await dashboard_service.get_recent_activities(current_user.id, limit=10)

        stats = DashboardStatsResponse(**stats_data)
        recent_projects = [DashboardProjectResponse(**project) for project in recent_projects_data]
        recent_activities = [_build_activity_response(activity) for activity in activities_data]

        return DashboardOverviewResponse(
            stats=stats, recentProjects=recent_projects, recentActivities=recent_activities
        )

    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard overview",
        )


@router.get("/today-tasks")
async def get_today_tasks(
    dashboard_service: AsyncDashboardService = Depends(get_dashboard_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get tasks assigned to current user for today."""
    try:
        return await dashboard_service.get_today_tasks(current_user.id)

    except Exception as e:
        logger.error(f"Error getting today tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch today tasks"
        )


@router.get("/recent-projects")
async def get_recent_projects(
    dashboard_service: AsyncDashboardService = Depends(get_dashboard_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get recent projects for current user."""
    try:
        return await dashboard_service.get_recent_projects(current_user.id, limit=5)
    except Exception as e:
        logger.error(f"Error getting recent projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recent projects",
        )


@router.get("/team-activity")
async def get_team_activity(
    dashboard_service: AsyncDashboardService = Depends(get_dashboard_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get recent team activity."""
    try:
        return await dashboard_service.get_recent_activities(current_user.id, limit=20)
    except Exception as e:
        logger.error(f"Error getting team activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team activity",
        )
