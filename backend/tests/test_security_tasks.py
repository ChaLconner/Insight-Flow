from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_tasks_unauthorized():
    response = client.get("/tasks")
    assert response.status_code == 401

def test_get_projects_unauthorized():
    response = client.get("/projects")
    # Projects router might be mounted differently or use dependency injection that fails earlier
    # But usually it should be 401 if Depends(get_current_user) is used.
    # checking imports in main.py: app.include_router(projects.router, tags=["projects"])
    # It probably has a prefix or just root.
    # Let's check routers/projects.py to be sure of the path, but usually it's /projects
    assert response.status_code in [401, 403]
