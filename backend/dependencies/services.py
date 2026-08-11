"""
Service dependency injection for FastAPI routers.
Provides centralized service instantiation with proper session management.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from services.async_analytics_service import AsyncAnalyticsService
from services.async_dashboard_service import AsyncDashboardService
from services.async_notification_service import AsyncNotificationService
from services.async_notification_trigger_service import AsyncNotificationTriggerService
from services.async_password_reset_service import AsyncPasswordResetService

# Import services
from services.async_project_service import AsyncProjectService
from services.async_task_history_service import AsyncTaskHistoryService
from services.async_task_service import AsyncTaskService
from services.async_usage_service import AsyncUsageService
from services.async_user_service import AsyncUserService


def get_project_service(db: AsyncSession = Depends(get_async_db)) -> AsyncProjectService:
    """
    Dependency to get AsyncProjectService instance.

    Usage:
        @router.get("/projects")
        async def get_projects(
            project_service: AsyncProjectService = Depends(get_project_service)
        ):
            ...
    """
    return AsyncProjectService(db)


def get_user_service(db: AsyncSession = Depends(get_async_db)) -> AsyncUserService:
    """
    Dependency to get AsyncUserService instance.

    Usage:
        @router.get("/users")
        async def get_users(
            user_service: AsyncUserService = Depends(get_user_service)
        ):
            ...
    """
    return AsyncUserService(db)


def get_notification_service(
    db: AsyncSession = Depends(get_async_db),
) -> AsyncNotificationTriggerService:
    """
    Dependency to get AsyncNotificationTriggerService instance.

    Usage:
        async def send_notification(
            notification_service: AsyncNotificationTriggerService = Depends(get_notification_service)
        ):
            ...
    """
    return AsyncNotificationTriggerService(db)


def get_password_reset_service(
    db: AsyncSession = Depends(get_async_db),
) -> AsyncPasswordResetService:
    """
    Dependency to get AsyncPasswordResetService instance.
    """
    return AsyncPasswordResetService(db)


def get_dashboard_service(db: AsyncSession = Depends(get_async_db)) -> AsyncDashboardService:
    """
    Dependency to get AsyncDashboardService instance.

    Usage:
        @router.get("/dashboard/overview")
        async def get_overview(
            dashboard_service: AsyncDashboardService = Depends(get_dashboard_service)
        ):
            ...
    """
    return AsyncDashboardService(db)


def get_task_service(db: AsyncSession = Depends(get_async_db)) -> AsyncTaskService:
    """
    Dependency to get AsyncTaskService instance.

    Usage:
        @router.get("/tasks")
        async def get_tasks(
            task_service: AsyncTaskService = Depends(get_task_service)
        ):
            ...
    """
    return AsyncTaskService(db)


def get_analytics_service(db: AsyncSession = Depends(get_async_db)) -> AsyncAnalyticsService:
    """
    Dependency to get AsyncAnalyticsService instance.
    """
    return AsyncAnalyticsService(db)


def get_task_history_service(
    db: AsyncSession = Depends(get_async_db),
) -> AsyncTaskHistoryService:
    """
    Dependency to get AsyncTaskHistoryService instance.
    """
    return AsyncTaskHistoryService(db)


def get_async_notification_service(
    db: AsyncSession = Depends(get_async_db),
) -> AsyncNotificationService:
    """
    Dependency to get AsyncNotificationService instance.
    """
    return AsyncNotificationService(db)


def get_usage_service(db: AsyncSession = Depends(get_async_db)) -> AsyncUsageService:
    """
    Dependency to get AsyncUsageService instance.
    """
    return AsyncUsageService(db)
