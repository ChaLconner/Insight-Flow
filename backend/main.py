from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, users, projects, tasks, analytics, notifications

app = FastAPI(
    title="Insight-Flow API",
    version="1.0.0",
    redirect_slashes=True  # Automatically handle trailing slashes
)

# Allow frontend (Next.js) to call API
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes    
)

# Include routers
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(analytics.router)
app.include_router(auth.router)
app.include_router(notifications.router)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI"}

@app.get("/minimal-test")
def minimal_test():
    """Minimal test endpoint to check if FastAPI is responsive."""
    return {"status": "success", "message": "Minimal test working"}

