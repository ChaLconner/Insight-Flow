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


async def get_project_service(db: AsyncSession = Depends(get_async_db)) -> AsyncProjectService:
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


async def get_user_service(db: AsyncSession = Depends(get_async_db)) -> AsyncUserService:
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


async def get_notification_service(
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


async def get_password_reset_service(
    db: AsyncSession = Depends(get_async_db),
) -> AsyncPasswordResetService:
    """
    Dependency to get AsyncPasswordResetService instance.
    """
    return AsyncPasswordResetService(db)


async def get_dashboard_service(db: AsyncSession = Depends(get_async_db)) -> AsyncDashboardService:
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


async def get_task_service(db: AsyncSession = Depends(get_async_db)) -> AsyncTaskService:
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


async def get_analytics_service(db: AsyncSession = Depends(get_async_db)) -> AsyncAnalyticsService:
    """
    Dependency to get AsyncAnalyticsService instance.
    """
    return AsyncAnalyticsService(db)


async def get_task_history_service(
    db: AsyncSession = Depends(get_async_db),
) -> AsyncTaskHistoryService:
    """
    Dependency to get AsyncTaskHistoryService instance.
    """
    return AsyncTaskHistoryService(db)


async def get_async_notification_service(
    db: AsyncSession = Depends(get_async_db),
) -> AsyncNotificationService:
    """
    Dependency to get AsyncNotificationService instance.
    """
    return AsyncNotificationService(db)


async def get_usage_service(db: AsyncSession = Depends(get_async_db)) -> AsyncUsageService:
    """
    Dependency to get AsyncUsageService instance.
    """
    return AsyncUsageService(db)


# Convenience function to get multiple services at once
class ServiceContainer:
    """Container for multiple services with shared session."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._project_service: AsyncProjectService | None = None
        self._user_service: AsyncUserService | None = None
        self._notification_service: AsyncNotificationTriggerService | None = None
        self._dashboard_service: AsyncDashboardService | None = None
        self._task_service: AsyncTaskService | None = None
        self._analytics_service: AsyncAnalyticsService | None = None
        self._task_history_service: AsyncTaskHistoryService | None = None
        self._async_notification_service: AsyncNotificationService | None = None
        self._usage_service: AsyncUsageService | None = None

    @property
    def project(self) -> AsyncProjectService:
        if self._project_service is None:
            self._project_service = AsyncProjectService(self.db)
        return self._project_service

    @property
    def user(self) -> AsyncUserService:
        if self._user_service is None:
            self._user_service = AsyncUserService(self.db)
        return self._user_service

    @property
    def notification(self) -> AsyncNotificationTriggerService:
        if self._notification_service is None:
            self._notification_service = AsyncNotificationTriggerService(self.db)
        return self._notification_service

    @property
    def dashboard(self) -> AsyncDashboardService:
        if self._dashboard_service is None:
            self._dashboard_service = AsyncDashboardService(self.db)
        return self._dashboard_service

    @property
    def task(self) -> AsyncTaskService:
        if self._task_service is None:
            self._task_service = AsyncTaskService(self.db)
        return self._task_service

    @property
    def analytics(self) -> AsyncAnalyticsService:
        if self._analytics_service is None:
            self._analytics_service = AsyncAnalyticsService(self.db)
        return self._analytics_service

    @property
    def task_history(self) -> AsyncTaskHistoryService:
        if self._task_history_service is None:
            self._task_history_service = AsyncTaskHistoryService(self.db)
        return self._task_history_service

    @property
    def async_notification(self) -> AsyncNotificationService:
        if self._async_notification_service is None:
            self._async_notification_service = AsyncNotificationService(self.db)
        return self._async_notification_service

    @property
    def usage(self) -> AsyncUsageService:
        if self._usage_service is None:
            self._usage_service = AsyncUsageService(self.db)
        return self._usage_service


async def get_services(db: AsyncSession = Depends(get_async_db)) -> ServiceContainer:
    """
    Get a service container with lazy-loaded services.
    Useful when you need multiple services in a single endpoint.

    Usage:
        @router.post("/projects/{project_id}/members")
        async def add_member(
            services: ServiceContainer = Depends(get_services)
        ):
            project = await services.project.get_project_by_id(project_id)
            await services.notification.notify_project_member_added(...)
    """
    return ServiceContainer(db)
