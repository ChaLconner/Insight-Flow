"""
FastAPI Application Entry Point.
Refactored for better maintainability - health endpoints and middleware moved to separate modules.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from config import get_settings
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
    tasks,
    usage,
    users,
)
from services.scheduler import shutdown_scheduler, start_scheduler
from utils.logger import app_logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup logic
    app_logger.info("=" * 50)
    app_logger.info("FASTAPI SERVER STARTING UP (LIFESPAN)")
    app_logger.info(f"Environment: {settings.environment}")

    # Initialize database connection
    try:
        await init_database()
        app_logger.info("Database initialized successfully")
    except Exception as e:
        app_logger.warning(f"Database initialization failed: {e}")
        app_logger.info("Continuing with mock authentication...")

    # Start background scheduler
    try:
        start_scheduler()
        app_logger.info("Background scheduler started")
    except Exception as e:
        app_logger.error(f"Failed to start scheduler: {e}")

    app_logger.info("=" * 50)
    app_logger.info(f"Server accessible at: http://{settings.host}:{settings.port}")
    app_logger.info("=" * 50)

    yield

    # Shutdown logic
    shutdown_scheduler()
    app_logger.info("FASTAPI SERVER SHUTTING DOWN")


# Create FastAPI application
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
    lifespan=lifespan,
)

# Mount static files
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup all middleware (CORS, security, rate limiting, etc.)
setup_all_middleware(app)

# Setup rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore

# Register exception handlers
add_exception_handlers(app)

# API Version prefix
API_V1_PREFIX = "/api/v1"

# Include routers with API versioning
app.include_router(projects.router, prefix=API_V1_PREFIX, tags=["projects"])
app.include_router(tasks.router, prefix=f"{API_V1_PREFIX}/tasks", tags=["tasks"])
app.include_router(analytics.router, prefix=f"{API_V1_PREFIX}/analytics", tags=["analytics"])
app.include_router(users.router, prefix=API_V1_PREFIX, tags=["users"])
app.include_router(auth.router, prefix=API_V1_PREFIX, tags=["auth"])
app.include_router(dashboard.router, prefix=API_V1_PREFIX, tags=["dashboard"])
app.include_router(notifications.router, prefix=API_V1_PREFIX)
app.include_router(files.router, prefix=API_V1_PREFIX)
app.include_router(project_tasks.router, prefix=API_V1_PREFIX, tags=["project tasks"])
app.include_router(payment.router, prefix=API_V1_PREFIX, tags=["payment"])
app.include_router(usage.router, prefix=API_V1_PREFIX, tags=["usage"])
app.include_router(favorites.router, prefix=API_V1_PREFIX, tags=["favorites"])

# Include health router (no prefix - these are root-level endpoints)
app.include_router(health.router)
