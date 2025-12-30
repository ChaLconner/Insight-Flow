"""
Services for Insight-Flow application.

This module exports ONLY async services.
Sync services have been removed for better performance and code consistency.
"""

# =============================================================================
# ASYNC SERVICES (All services are now async)
# =============================================================================
from .async_analytics_service import AsyncAnalyticsService
from .async_dashboard_service import AsyncDashboardService
from .async_deadline_reminder import AsyncDeadlineReminderService, run_async_deadline_check
from .async_notification_service import AsyncNotificationService
from .async_notification_trigger_service import AsyncNotificationTriggerService
from .async_password_reset_service import AsyncPasswordResetService
from .async_project_service import AsyncProjectService
from .async_task_history_service import AsyncTaskHistoryService
from .async_task_service import AsyncTaskService
from .async_user_service import AsyncUserService

# =============================================================================
# SUPPORT SERVICES (no async version needed)
# =============================================================================
from .cache_service import CacheService, cache_service
from .notification_rate_limiter import NotificationRateLimiter
from .payment_service import PaymentService
from .scheduler import shutdown_scheduler, start_scheduler

__all__ = [
    "AsyncAnalyticsService",
    "AsyncDashboardService",
    "AsyncDeadlineReminderService",
    "AsyncNotificationService",
    "AsyncNotificationTriggerService",
    "AsyncPasswordResetService",
    "AsyncProjectService",
    "AsyncTaskHistoryService",
    "AsyncTaskService",
    "AsyncUserService",
    "CacheService",
    "NotificationRateLimiter",
    "PaymentService",
    "cache_service",
    "run_async_deadline_check",
    "shutdown_scheduler",
    "start_scheduler",
]
