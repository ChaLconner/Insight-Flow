from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, users, projects, tasks, analytics, notifications

app = FastAPI(title="Insight-Flow API", version="1.0.0")

# Allow frontend (Next.js) to call API
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return {"message": "Hello from FastAPI 🚀"}
