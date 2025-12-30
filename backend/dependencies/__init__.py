"""
Unified Dependencies Package for Insight-Flow application.

This package provides clean dependency injection for all routers.
Import directly from this package for cleaner imports:

    from dependencies import require_project_member, get_project_service
"""

# Re-export everything from async_dependencies
from async_dependencies import (
    AsyncProjectPermission,
    get_async_authorized_task,
    get_authorized_task,
    require_project_admin,
    require_project_member,
    require_project_owner,
)

# Auth dependency injection
from .auth import (
    get_current_active_user,
    get_current_active_user_optional,
    get_current_user,
    get_current_user_optional,
    get_token_from_cookie_or_header,
    oauth2_scheme,
)

# Service dependency injection
from .services import (
    ServiceContainer,
    get_analytics_service,
    get_dashboard_service,
    get_notification_service,
    get_password_reset_service,
    get_project_service,
    get_services,
    get_task_service,
    get_user_service,
)

__all__ = [
    "AsyncProjectPermission",
    "ServiceContainer",
    "get_analytics_service",
    "get_async_authorized_task",
    "get_authorized_task",
    "get_current_active_user",
    "get_current_active_user_optional",
    "get_current_user",
    "get_current_user_optional",
    "get_dashboard_service",
    "get_notification_service",
    "get_password_reset_service",
    "get_project_service",
    "get_services",
    "get_task_service",
    "get_token_from_cookie_or_header",
    "get_user_service",
    "oauth2_scheme",
    "require_project_admin",
    "require_project_member",
    "require_project_owner",
]
