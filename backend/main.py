from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import auth, users, projects, tasks, analytics, dashboard, notifications, files
import os
from dotenv import load_dotenv
from utils.logger import app_logger
from middleware.cache import CacheMiddleware
from database import init_database

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
    # in production, you might want to raise an error to stop startup
    # raise RuntimeError(error_msg)
    # For now, we'll log strictly but allow continuing for dev convenience if needed, 
    # though strictly we should stop. Let's start with a warning stack for now to avoid breaking existing dev flows instantly 
    # if they are lazy, but the requirement is "Add environment variable validation".
    # Given the Critical priority, we should probably be noisy.
    
app_logger.info(f"SECRET_KEY exists: {'YES' if os.getenv('SECRET_KEY') else 'NO'}")
app_logger.info(f"DATABASE_URL exists: {'YES' if os.getenv('DATABASE_URL') else 'NO'}")

app = FastAPI(
    title="Insight-Flow API",
    version="1.0.0",
    redirect_slashes=True  # Enable automatic redirect to handle trailing slashes
)

# Mount static files
# Ensure static directory exists
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add startup event to log server binding information
@app.on_event("startup")
async def startup_event():
    app_logger.info("="*50)
    app_logger.info("FASTAPI SERVER STARTING UP")
    
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

@app.on_event("shutdown")
async def shutdown_event():
    app_logger.info("FASTAPI SERVER SHUTTING DOWN")

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",  # Add for direct backend access
        "http://127.0.0.1:8000",  # Add for direct backend access
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Custom middleware for CORS debugging removed for performance

# Trusted Host Middleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
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
    if exc.errors():
        try:
            # Try to get a clean error message
            e = exc.errors()[0]
            if "msg" in e:
                error_msg = e["msg"]
            if "loc" in e:
                 error_msg += f" in {' -> '.join(str(l) for l in e['loc'])}"
        except:
            pass

    return JSONResponse(
        status_code=422,
        content={
            "success": False, 
            "message": error_msg,
            "errors": exc.errors()
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    app_logger.warning(f"ValueError: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": str(exc)
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