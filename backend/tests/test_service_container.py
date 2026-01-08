"""
Tests for ServiceContainer and service dependency injection.
Covers dependencies/services.py for increased coverage.
"""

from unittest.mock import AsyncMock

import pytest


class TestServiceContainer:
    """Tests for ServiceContainer lazy initialization."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    def test_service_container_initialization(self, mock_db):
        """Test ServiceContainer initializes with db session."""
        from dependencies.services import ServiceContainer

        container = ServiceContainer(mock_db)

        assert container.db == mock_db
        assert container._project_service is None
        assert container._user_service is None
        assert container._notification_service is None
        assert container._dashboard_service is None
        assert container._task_service is None
        assert container._analytics_service is None
        assert container._task_history_service is None
        assert container._async_notification_service is None

    def test_project_service_lazy_loading(self, mock_db):
        """Test project service is lazily loaded."""
        from dependencies.services import ServiceContainer
        from services.async_project_service import AsyncProjectService

        container = ServiceContainer(mock_db)

        # Initially None
        assert container._project_service is None

        # Access triggers lazy load
        service = container.project

        assert service is not None
        assert isinstance(service, AsyncProjectService)
        assert container._project_service is service

        # Second access returns same instance
        service2 = container.project
        assert service2 is service

    def test_user_service_lazy_loading(self, mock_db):
        """Test user service is lazily loaded."""
        from dependencies.services import ServiceContainer
        from services.async_user_service import AsyncUserService

        container = ServiceContainer(mock_db)

        assert container._user_service is None

        service = container.user

        assert service is not None
        assert isinstance(service, AsyncUserService)
        assert container._user_service is service

        # Second access returns same instance
        service2 = container.user
        assert service2 is service

    def test_notification_service_lazy_loading(self, mock_db):
        """Test notification service is lazily loaded."""
        from dependencies.services import ServiceContainer
        from services.async_notification_trigger_service import (
            AsyncNotificationTriggerService,
        )

        container = ServiceContainer(mock_db)

        assert container._notification_service is None

        service = container.notification

        assert service is not None
        assert isinstance(service, AsyncNotificationTriggerService)
        assert container._notification_service is service

    def test_dashboard_service_lazy_loading(self, mock_db):
        """Test dashboard service is lazily loaded."""
        from dependencies.services import ServiceContainer
        from services.async_dashboard_service import AsyncDashboardService

        container = ServiceContainer(mock_db)

        assert container._dashboard_service is None

        service = container.dashboard

        assert service is not None
        assert isinstance(service, AsyncDashboardService)
        assert container._dashboard_service is service

    def test_task_service_lazy_loading(self, mock_db):
        """Test task service is lazily loaded."""
        from dependencies.services import ServiceContainer
        from services.async_task_service import AsyncTaskService

        container = ServiceContainer(mock_db)

        assert container._task_service is None

        service = container.task

        assert service is not None
        assert isinstance(service, AsyncTaskService)
        assert container._task_service is service

    def test_analytics_service_lazy_loading(self, mock_db):
        """Test analytics service is lazily loaded."""
        from dependencies.services import ServiceContainer
        from services.async_analytics_service import AsyncAnalyticsService

        container = ServiceContainer(mock_db)

        assert container._analytics_service is None

        service = container.analytics

        assert service is not None
        assert isinstance(service, AsyncAnalyticsService)
        assert container._analytics_service is service

    def test_task_history_service_lazy_loading(self, mock_db):
        """Test task history service is lazily loaded."""
        from dependencies.services import ServiceContainer
        from services.async_task_history_service import AsyncTaskHistoryService

        container = ServiceContainer(mock_db)

        assert container._task_history_service is None

        service = container.task_history

        assert service is not None
        assert isinstance(service, AsyncTaskHistoryService)
        assert container._task_history_service is service

    def test_async_notification_service_lazy_loading(self, mock_db):
        """Test async notification service is lazily loaded."""
        from dependencies.services import ServiceContainer
        from services.async_notification_service import AsyncNotificationService

        container = ServiceContainer(mock_db)

        assert container._async_notification_service is None

        service = container.async_notification

        assert service is not None
        assert isinstance(service, AsyncNotificationService)
        assert container._async_notification_service is service

    def test_all_services_share_same_db(self, mock_db):
        """Test all services use the same database session."""
        from dependencies.services import ServiceContainer

        container = ServiceContainer(mock_db)

        # Access all services
        project = container.project
        user = container.user
        notification = container.notification
        dashboard = container.dashboard
        task = container.task
        analytics = container.analytics
        task_history = container.task_history
        async_notif = container.async_notification

        # All should have the same db
        assert project.db is mock_db
        assert user.db is mock_db
        assert notification.db is mock_db
        assert dashboard.db is mock_db
        assert task.db is mock_db
        assert analytics.db is mock_db
        assert task_history.db is mock_db
        assert async_notif.db is mock_db


class TestServiceDependencies:
    """Test service dependency functions."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        db = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_get_project_service(self, mock_db):
        """Test get_project_service returns AsyncProjectService."""
        from dependencies.services import get_project_service
        from services.async_project_service import AsyncProjectService

        service = await get_project_service(mock_db)

        assert isinstance(service, AsyncProjectService)
        assert service.db is mock_db

    @pytest.mark.asyncio
    async def test_get_user_service(self, mock_db):
        """Test get_user_service returns AsyncUserService."""
        from dependencies.services import get_user_service
        from services.async_user_service import AsyncUserService

        service = await get_user_service(mock_db)

        assert isinstance(service, AsyncUserService)
        assert service.db is mock_db

    @pytest.mark.asyncio
    async def test_get_notification_service(self, mock_db):
        """Test get_notification_service returns AsyncNotificationTriggerService."""
        from dependencies.services import get_notification_service
        from services.async_notification_trigger_service import (
            AsyncNotificationTriggerService,
        )

        service = await get_notification_service(mock_db)

        assert isinstance(service, AsyncNotificationTriggerService)
        assert service.db is mock_db

    @pytest.mark.asyncio
    async def test_get_password_reset_service(self, mock_db):
        """Test get_password_reset_service returns AsyncPasswordResetService."""
        from dependencies.services import get_password_reset_service
        from services.async_password_reset_service import AsyncPasswordResetService

        service = await get_password_reset_service(mock_db)

        assert isinstance(service, AsyncPasswordResetService)
        assert service.db is mock_db

    @pytest.mark.asyncio
    async def test_get_dashboard_service(self, mock_db):
        """Test get_dashboard_service returns AsyncDashboardService."""
        from dependencies.services import get_dashboard_service
        from services.async_dashboard_service import AsyncDashboardService

        service = await get_dashboard_service(mock_db)

        assert isinstance(service, AsyncDashboardService)
        assert service.db is mock_db

    @pytest.mark.asyncio
    async def test_get_task_service(self, mock_db):
        """Test get_task_service returns AsyncTaskService."""
        from dependencies.services import get_task_service
        from services.async_task_service import AsyncTaskService

        service = await get_task_service(mock_db)

        assert isinstance(service, AsyncTaskService)
        assert service.db is mock_db

    @pytest.mark.asyncio
    async def test_get_analytics_service(self, mock_db):
        """Test get_analytics_service returns AsyncAnalyticsService."""
        from dependencies.services import get_analytics_service
        from services.async_analytics_service import AsyncAnalyticsService

        service = await get_analytics_service(mock_db)

        assert isinstance(service, AsyncAnalyticsService)
        assert service.db is mock_db

    @pytest.mark.asyncio
    async def test_get_task_history_service(self, mock_db):
        """Test get_task_history_service returns AsyncTaskHistoryService."""
        from dependencies.services import get_task_history_service
        from services.async_task_history_service import AsyncTaskHistoryService

        service = await get_task_history_service(mock_db)

        assert isinstance(service, AsyncTaskHistoryService)
        assert service.db is mock_db

    @pytest.mark.asyncio
    async def test_get_async_notification_service(self, mock_db):
        """Test get_async_notification_service returns AsyncNotificationService."""
        from dependencies.services import get_async_notification_service
        from services.async_notification_service import AsyncNotificationService

        service = await get_async_notification_service(mock_db)

        assert isinstance(service, AsyncNotificationService)
        assert service.db is mock_db

    @pytest.mark.asyncio
    async def test_get_services(self, mock_db):
        """Test get_services returns ServiceContainer."""
        from dependencies.services import ServiceContainer, get_services

        container = await get_services(mock_db)

        assert isinstance(container, ServiceContainer)
        assert container.db is mock_db
