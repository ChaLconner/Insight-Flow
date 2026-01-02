
import pytest
import uuid
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from dependencies.services import get_project_service, get_notification_service
from routers.auth import get_current_active_user
from async_dependencies import require_project_member, require_project_admin, require_project_owner
from models.user import User
from models.project import Project

# Mocks
@pytest.fixture
def mock_project_service():
    service = AsyncMock()
    return service

@pytest.fixture
def mock_notification_service():
    service = AsyncMock()
    return service

@pytest.fixture
def current_user():
    return User(id=uuid.uuid4(), email="test@example.com", name="Test User", role="member")

@pytest.fixture
def mock_project():
    return Project(id=uuid.uuid4(), name="Mock Project", owner_id=uuid.uuid4())

# Override Dependencies
@pytest.fixture
def client(mock_project_service, mock_notification_service, current_user, mock_project):
    
    async def override_get_project_service():
        return mock_project_service
        
    async def override_get_notification_service():
        return mock_notification_service
    
    async def override_get_current_active_user():
        return current_user

    async def override_require_project_member():
        # Just return the mock project, assuming permission check passed
        return mock_project

    async def override_require_project_admin():
        return mock_project

    async def override_require_project_owner():
        return mock_project

    app.dependency_overrides[get_project_service] = override_get_project_service
    app.dependency_overrides[get_notification_service] = override_get_notification_service
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    app.dependency_overrides[require_project_member] = override_require_project_member
    app.dependency_overrides[require_project_admin] = override_require_project_admin
    app.dependency_overrides[require_project_owner] = override_require_project_owner
    
    with TestClient(app) as c:
        yield c
        
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_builders():
    with patch("routers.projects.build_project_response") as b_pr, \
         patch("routers.projects.build_project_with_members_response") as b_pwmr, \
         patch("routers.projects.build_project_member_response") as b_pmr:
        
        # Setup defaults matching ProjectResponse schema
        base_resp = {
            "id": str(uuid.uuid4()), 
            "name": "Mock", 
            "description": "D", 
            "owner_id": str(uuid.uuid4()), 
            "is_active": True,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z", 
            "status": "active",
            "task_count": 0,
            "completed_tasks": 0,
            "overdue_tasks": 0,
            "recent_activity": 0,
            "member_count": 0,
            "member_summaries": []
        }
        
        b_pr.return_value = base_resp
        
        with_members_resp = base_resp.copy()
        with_members_resp["members"] = []
        b_pwmr.return_value = with_members_resp
        
        b_pmr.return_value = {
             "id": str(uuid.uuid4()),
             "project_id": str(uuid.uuid4()),
             "user_id": str(uuid.uuid4()), 
             "role": "member", 
             "joined_at": "2023-01-01T00:00:00Z",
             "user": {
                 "id": str(uuid.uuid4()), 
                 "email": "m@test.com", 
                 "name": "M",
                 "role": "member", 
                 "is_active": True,
                 "created_at": "2023-01-01T00:00:00Z", 
                 "updated_at": "2023-01-01T00:00:00Z",
                 "email_verified": True
             }
        }
        
        yield {"pr": b_pr, "pwmr": b_pwmr, "pmr": b_pmr}

# Tests

def test_create_project(client, mock_project_service):
    mock_project_service.create_project.return_value = Project(id=uuid.uuid4(), name="New Project")
    mock_project_service.get_project_with_details.return_value = {
        "project": Project(id=uuid.uuid4(), name="New Project"),
        "members": [],
        "task_counts": {},
        "activity": []
    }
    
    payload = {"name": "New Project", "description": "Desc"}
    response = client.post("/api/v1/projects", json=payload)
    
    # Use assertion message for debugging instead of print
    assert response.status_code == 200, f"Create project failed: {response.json()}"
    data = response.json()
    assert data["name"] == "Mock" # Comes from build_project_response mock
    # Verify service calls
    mock_project_service.create_project.assert_called_once()
    mock_project_service.get_project_with_details.assert_called_once()

def test_read_projects_list(client, mock_project_service):
    mock_project_service.get_projects_with_stats.return_value = [
        {
            "project": Project(id=uuid.uuid4(), name="P1"),
            "members": [],
            "task_counts": {},
            "activity": []
        }
    ]
    
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_read_project(client, mock_project_service, mock_project):
    mock_project_service.get_project_with_details.return_value = {
        "project": mock_project,
        "members": [],
        "task_counts": {},
        "activity": []
    }
    
    response = client.get(f"/api/v1/projects/{mock_project.id}")
    assert response.status_code == 200
    # Since builder is mocked to return static data, check for that
    assert response.json()["name"] == "Mock"

def test_update_project(client, mock_project_service, mock_project):
    mock_project_service.update_project.return_value = mock_project
    mock_project_service.get_project_with_details.return_value = {
        "project": mock_project,
        "members": [],
        "task_counts": {}
    }
    
    payload = {"name": "Updated Name"}
    response = client.put(f"/api/v1/projects/{mock_project.id}", json=payload)
    
    assert response.status_code == 200
    mock_project_service.update_project.assert_called_once()

def test_delete_project(client, mock_project_service, mock_project):
    response = client.delete(f"/api/v1/projects/{mock_project.id}")
    
    assert response.status_code == 200
    mock_project_service.delete_project.assert_called_once()

def test_read_project_members(client, mock_project_service, mock_project):
    mock_project_service.get_project_members.return_value = []
    
    response = client.get(f"/api/v1/projects/{mock_project.id}/members")
    
    assert response.status_code == 200
    assert response.json() == []

def test_add_project_member(client, mock_project_service, mock_notification_service, mock_project):
    # Mock return value needs a user model
    new_member_user = User(id=uuid.uuid4(), email="new@test.com")
    member_mock = MagicMock()
    member_mock.user = new_member_user
    member_mock.role = "member"
    
    mock_project_service.add_project_member.return_value = member_mock
    mock_project_service.get_project_by_id.return_value = mock_project
    
    payload = {"user_id": str(new_member_user.id), "role": "member"}
    # The endpoint route is /projects/{project_id}/members
    response = client.post(f"/api/v1/projects/{mock_project.id}/members", json=payload)
    
    assert response.status_code == 200
    # Check notification sent
    mock_notification_service.notify_project_member_added.assert_called_once()

def test_remove_project_member(client, mock_project_service, mock_project):
    uid = uuid.uuid4()
    response = client.delete(f"/api/v1/projects/{mock_project.id}/members/{uid}")
    
    assert response.status_code == 200
    mock_project_service.remove_project_member.assert_called_once()

def test_update_member_role(client, mock_project_service, mock_project):
    uid = uuid.uuid4()
    member_mock = MagicMock()
    member_mock.role = "admin"
    member_mock.user = User(id=uid)
    
    mock_project_service.update_member_role.return_value = member_mock
    
    payload = {"role": "admin"}
    response = client.put(f"/api/v1/projects/{mock_project.id}/members/{uid}/role", json=payload)
    
    assert response.status_code == 200
    mock_project_service.update_member_role.assert_called_once()
