from fastapi import FastAPI, Request
from sqlalchemy.exc import IntegrityError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import auth, users, projects, tasks, analytics, dashboard, notifications, files
import os
from dotenv import load_dotenv
from utils.logger import app_logger
from middleware.cache import CacheMiddleware
from database import init_database
from contextlib import asynccontextmanager

# Load environment variables at startup
load_dotenv()

# Log environment information using proper logger
app_logger.info("Environment loaded in main.py")

# Validate critical environment variables
required_vars = [
    "DATABASE_URL",
    "SECRET_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET"
]

missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    error_msg = f"CRITICAL ERROR: Missing required environment variables: {', '.join(missing_vars)}"
    app_logger.critical(error_msg)
    raise RuntimeError(error_msg)
    
app_logger.info(f"SECRET_KEY exists: {'YES' if os.getenv('SECRET_KEY') else 'NO'}")
app_logger.info(f"DATABASE_URL exists: {'YES' if os.getenv('DATABASE_URL') else 'NO'}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    app_logger.info("="*50)
    app_logger.info("FASTAPI SERVER STARTING UP (LIFESPAN)")
    
    # Initialize database connection
    try:
        init_database()
        app_logger.info("Database initialized successfully")
    except Exception as e:
        app_logger.warning(f"Database initialization failed: {e}")
        app_logger.info("Continuing with mock authentication...")
    
    app_logger.info("="*50)
    app_logger.info(f"Server should be accessible at: http://localhost:8000")
    app_logger.info(f"Database URL exists: {'YES' if os.getenv('DATABASE_URL') else 'NO'}")
    app_logger.info("="*50)

    yield
    
    # Shutdown logic
    app_logger.info("FASTAPI SERVER SHUTTING DOWN")

app = FastAPI(
    title="Insight-Flow API",
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
    version="1.0.0",
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
    ],
    redirect_slashes=True,
    lifespan=lifespan
)

# Mount static files
# Ensure static directory exists
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add startup event to log server binding information
# Startup and shutdown events removed in favor of lifespan

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Custom middleware for CORS debugging removed for performance

# Trusted Host Middleware
# Trusted Host Middleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Allow strictly configuring allowed hosts in production
allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,testserver").split(",")
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=allowed_hosts
)

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Standardize HTTP exceptions to match API response format.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(exc.detail),
            "code": exc.status_code
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Standardize validation errors.
    """
    # Get the first error message for the main message
    error_msg = "Validation Error"
    formatted_errors = []
    
    if exc.errors():
        try:
            # Try to get a clean error message
            e = exc.errors()[0]
            if "msg" in e:
                error_msg = e["msg"]
            if "loc" in e:
                 error_msg += f" in {' -> '.join(str(l) for l in e['loc'])}"
            
            # Format errors to be JSON serializable
            import json
            for e in exc.errors():
                # specific handling for 'ctx' which might contain exception objects
                error_dict = e.copy()
                if 'ctx' in error_dict:
                    # exceptions are not serializable, convert to str
                    if 'error' in error_dict['ctx']:
                         error_dict['ctx']['error'] = str(error_dict['ctx']['error'])
                if 'url' in error_dict:
                    error_dict.pop('url') # URL objects might cause issues too
                formatted_errors.append(error_dict)
                
        except Exception as e:
            app_logger.error(f"Error formatting validation exception: {e}")
            formatted_errors = [{"msg": str(exc)}]

    return JSONResponse(
        status_code=422,
        content={
            "success": False, 
            "message": error_msg,
            "errors": formatted_errors
        }
    )

from utils.exceptions import AppError

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """
    Handle standardized AppErrors.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "code": exc.code,
            "details": exc.details
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    app_logger.warning(f"ValueError: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": str(exc),
            "code": "BAD_REQUEST"
        }
    )

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    app_logger.warning(f"IntegrityError: {exc}")
    # Try to extract clearer message
    msg = "Database constraint violation"
    if hasattr(exc, 'orig') and str(exc.orig):
        if 'unique constraint' in str(exc.orig).lower():
             msg = "Duplicate entry detected"
    
    return JSONResponse(
        status_code=409,
        content={
            "success": False,
            "message": msg,
            "detail": str(exc)
        }
    )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = os.urandom(4).hex()
    app_logger.error(f"Unhandled exception {error_id}: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal Server Error",
            "error_id": error_id,
            "detail": str(exc) if os.getenv("ENVIRONMENT") == "development" else None
        }
    )

from middleware.monitoring import PerformanceMiddleware

app.add_middleware(PerformanceMiddleware)
app.add_middleware(CacheMiddleware, cache_timeout=60)

# Include routers - order matters for overlapping routes!
app.include_router(projects.router, tags=["projects"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(users.router, tags=["users"])
app.include_router(auth.router, tags=["auth"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(notifications.router)
app.include_router(files.router)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI"}

@app.get("/minimal-test")
def minimal_test():
    """Minimal test endpoint to check if FastAPI is responsive."""
    return {"status": "success", "message": "Minimal test working"}

@app.get("/test-auth")
def test_auth():
    """Test endpoint to check authentication."""
    return {"message": "Auth test endpoint"}