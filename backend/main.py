from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, users, projects, tasks, analytics, dashboard
import os
from dotenv import load_dotenv
from utils.logger import app_logger
from middleware.cache import CacheMiddleware
from database import init_database

# Load environment variables at startup
load_dotenv()

# Log environment information using proper logger
app_logger.info("Environment loaded in main.py")
app_logger.info(f"SECRET_KEY exists: {'YES' if os.getenv('SECRET_KEY') else 'NO'}")
app_logger.info(f"DATABASE_URL exists: {'YES' if os.getenv('DATABASE_URL') else 'NO'}")

# Allow frontend (Next.js) to call API
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",  # Alternative port for development
    "http://127.0.0.1:3001",
]

app = FastAPI(
    title="Insight-Flow API",
    version="1.0.0",
    redirect_slashes=True  # Enable automatic redirect to handle trailing slashes
)

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
    app_logger.info(f"CORS origins allowed: {origins}")
    app_logger.info(f"Database URL exists: {'YES' if os.getenv('DATABASE_URL') else 'NO'}")
    app_logger.info("="*50)

@app.on_event("shutdown")
async def shutdown_event():
    app_logger.info("FASTAPI SERVER SHUTTING DOWN")
app.add_middleware(CacheMiddleware, cache_timeout=300)

# Add CORS middleware with detailed logging
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],  # Allow localhost ports
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Add custom middleware for CORS debugging
@app.middleware("http")
async def log_cors(request: Request, call_next):
    app_logger.info(f"[CORS] Incoming request: {request.method} {request.url}")
    app_logger.info(f"[CORS] Origin: {request.headers.get('origin')}")
    app_logger.info(f"[CORS] Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    app_logger.info(f"[CORS] Response status: {response.status_code}")
    app_logger.info(f"[CORS] Response headers: {dict(response.headers)}")
    
    return response

# Include routers - order matters for overlapping routes!
app.include_router(projects.router, tags=["projects"])
app.include_router(tasks.router, tags=["tasks"])
app.include_router(analytics.router, tags=["analytics"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(auth.router, tags=["auth"])
app.include_router(dashboard.router, tags=["dashboard"])

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