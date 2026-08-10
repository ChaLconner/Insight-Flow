"""
FastAPI Application Entry Point.
Refactored for better maintainability - health endpoints and middleware moved to separate modules.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from config import AppSettings, get_settings
from core.middleware_config import setup_all_middleware
from database import init_database
from exception_handlers import add_exception_handlers
from rate_limiter import limiter, rate_limit_exceeded_handler
from routers import (
    analytics,
    auth,
    dashboard,
    favorites,
    files,
    health,
    notifications,
    payment,
    project_tasks,
    projects,
    security_logs,
    tasks,
    usage,
    users,
)
from services.scheduler import shutdown_scheduler, start_scheduler
from utils.logger import app_logger


def _build_lifespan(settings: AppSettings):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan manager for startup and shutdown."""
        app_logger.info("=" * 50)
        app_logger.info("FASTAPI SERVER STARTING UP (LIFESPAN)")
        app_logger.info(f"Environment: {settings.environment}")

        try:
            await init_database()
            app_logger.info("Database initialized successfully")
        except Exception as e:
            if settings.is_production:
                app_logger.critical(f"Database initialization failed in production: {e}")
                raise RuntimeError("Database initialization failed in production") from e
            app_logger.warning(f"Database initialization failed: {e}")
            app_logger.info("Continuing without database-backed functionality in non-production.")

        if settings.scheduler_enabled:
            try:
                start_scheduler()
                app_logger.info("Background scheduler started")
            except Exception as e:
                app_logger.error(f"Failed to start scheduler: {e}")
        else:
            app_logger.info("Background scheduler disabled for this process")

        app_logger.info("=" * 50)
        app_logger.info(f"Server accessible at: http://{settings.host}:{settings.port}")
        app_logger.info("=" * 50)

        yield

        if settings.scheduler_enabled:
            shutdown_scheduler()
        try:
            from database import async_engine
            from services.cache_service import cache_service

            await cache_service.close()
            if async_engine is not None:
                await async_engine.dispose()
        except Exception as e:
            app_logger.warning(f"Failed to release shared resources during shutdown: {e}")
        app_logger.info("FASTAPI SERVER SHUTTING DOWN")

    return lifespan


def create_app(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or get_settings()
    docs_enabled = getattr(settings, "docs_enabled", None)
    if docs_enabled is None:
        docs_enabled = settings.enable_docs
        if settings.is_production:
            docs_enabled = False

    app = FastAPI(
        title=settings.app_name,
        description="""
## Insight-Flow Project Management API

A comprehensive project management and team collaboration platform.

### Features
- **Projects**: Create and manage projects with team members
- **Tasks**: Full task lifecycle management with assignments and status tracking
- **Dashboard**: Real-time analytics and progress tracking
- **Notifications**: Event-driven notification system
- **Authentication**: Secure JWT-based authentication with Google OAuth support

### Authentication
Most endpoints require authentication via JWT token stored in HTTP-only cookies.
Use `/auth/login` to authenticate and `/auth/logout` to terminate sessions.

### Rate Limiting
API requests are rate-limited. Please contact support for higher limits.
    """,
        version=settings.api_version,
        terms_of_service="https://example.com/terms/",
        contact={
            "name": "Insight-Flow Support",
            "email": "support@insight-flow.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        openapi_tags=[
            {
                "name": "auth",
                "description": "Authentication operations - login, logout, token refresh, OAuth",
            },
            {
                "name": "users",
                "description": "User management - profiles, settings, search",
            },
            {
                "name": "projects",
                "description": "Project CRUD operations and member management",
            },
            {
                "name": "tasks",
                "description": "Task management - create, update, assign, track status",
            },
            {
                "name": "dashboard",
                "description": "Dashboard statistics and analytics overview",
            },
            {
                "name": "analytics",
                "description": "Detailed project analytics and metrics",
            },
            {
                "name": "notifications",
                "description": "User notifications and alerts",
            },
            {
                "name": "files",
                "description": "File upload and management",
            },
            {
                "name": "health",
                "description": "Health checks and metrics for monitoring",
            },
            {
                "name": "favorites",
                "description": "User favorite projects management",
            },
        ],
        redirect_slashes=True,
        lifespan=_build_lifespan(settings),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    setup_all_middleware(app)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore

    add_exception_handlers(app)

    api_v1_prefix = "/api/v1"
    app.include_router(projects.router, prefix=api_v1_prefix, tags=["projects"])
    app.include_router(tasks.router, prefix=f"{api_v1_prefix}/tasks", tags=["tasks"])
    app.include_router(analytics.router, prefix=f"{api_v1_prefix}/analytics", tags=["analytics"])
    app.include_router(users.router, prefix=api_v1_prefix, tags=["users"])
    app.include_router(auth.router, prefix=api_v1_prefix, tags=["auth"])
    app.include_router(dashboard.router, prefix=api_v1_prefix, tags=["dashboard"])
    app.include_router(notifications.router, prefix=api_v1_prefix)
    app.include_router(files.router, prefix=api_v1_prefix)
    app.include_router(project_tasks.router, prefix=api_v1_prefix, tags=["project tasks"])
    app.include_router(payment.router, prefix=api_v1_prefix, tags=["payment"])
    app.include_router(usage.router, prefix=api_v1_prefix, tags=["usage"])
    app.include_router(favorites.router, prefix=api_v1_prefix, tags=["favorites"])
    app.include_router(security_logs.router, prefix=api_v1_prefix, tags=["security"])
    app.include_router(health.router)

    return app


app = create_app()
