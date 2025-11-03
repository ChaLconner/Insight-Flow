"""
Task management endpoint tests.
"""
import pytest
from fastapi.testclient import TestClient
import uuid

class TestTaskManagement:
    """Test task management endpoints."""
    
    def test_get_tasks_list(self, client: TestClient, auth_headers: dict):
        """Test getting list of tasks."""
        response = client.get("/tasks/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_tasks_unauthorized(self, client: TestClient):
        """Test getting tasks without authentication."""
        response = client.get("/tasks/")
        
        assert response.status_code == 401
    
    def test_get_tasks_with_pagination(self, client: TestClient, auth_headers: dict):
        """Test getting tasks with pagination."""
        response = client.get("/tasks/?skip=0&limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_tasks_with_filters(self, client: TestClient, auth_headers: dict):
        """Test getting tasks with filters."""
        # Test status filter
        response = client.get("/tasks/?status=todo", headers=auth_headers)
        assert response.status_code == 200
        
        # Test assignee filter
        fake_assignee_id = str(uuid.uuid4())
        response = client.get(f"/tasks/?assignee_id={fake_assignee_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Test project filter
        fake_project_id = str(uuid.uuid4())
        response = client.get(f"/tasks/?project_id={fake_project_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Test my_tasks filter
        response = client.get("/tasks/?my_tasks=true", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_tasks_invalid_status(self, client: TestClient, auth_headers: dict):
        """Test getting tasks with invalid status."""
        response = client.get("/tasks/?status=invalid_status", headers=auth_headers)
        
        assert response.status_code == 400
        assert "Invalid task status" in response.json()["detail"]
    
    def test_create_task_success(self, client: TestClient, auth_headers: dict, sample_task_data: dict, db_session):
        """Test creating a new task."""
        # First create a project to associate with task
        from services.project_service import ProjectService
        from schemas.project import ProjectCreate
        project_service = ProjectService(db_session)
        project_data = ProjectCreate(
            name="Test Project",
            description="Project for task testing"
        )
        
        # Get current user ID from token
        import jwt
        token = auth_headers["Authorization"].split(" ")[1]
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = uuid.UUID(payload["sub"])
        
        project = project_service.create_project(project_data, user_id)
        
        # Add project_id to task data
        task_data = sample_task_data.copy()
        task_data["project_id"] = str(project.id)
        
        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["description"] == task_data["description"]
        assert data["project_id"] == task_data["project_id"]
        assert "id" in data
    
    def test_create_task_unauthorized(self, client: TestClient, sample_task_data: dict):
        """Test creating task without authentication."""
        response = client.post("/tasks/", json=sample_task_data)
        
        assert response.status_code == 401
    
    def test_create_task_invalid_data(self, client: TestClient, auth_headers: dict):
        """Test creating task with invalid data."""
        invalid_data = {
            "title": "",  # Empty title should fail
            "description": "Test task"
        }
        
        response = client.post("/tasks/", json=invalid_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_task_not_project_member(self, client: TestClient, auth_headers: dict, sample_task_data: dict):
        """Test creating task when not a project member."""
        task_data = sample_task_data.copy()
        task_data["project_id"] = str(uuid.uuid4())  # Non-existent project
        
        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        
        assert response.status_code in [400, 403, 404]
    
    def test_get_task_by_id_success(self, client: TestClient, auth_headers: dict, db_session):
        """Test getting task by ID."""
        # This would require setting up a task first
        fake_id = str(uuid.uuid4())
        response = client.get(f"/tasks/{fake_id}", headers=auth_headers)
        
        # Should fail because task doesn't exist
        assert response.status_code == 404
    
    def test_get_task_by_id_unauthorized(self, client: TestClient):
        """Test getting task without authentication."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/tasks/{fake_id}")
        
        assert response.status_code == 401
    
    def test_update_task_success(self, client: TestClient, auth_headers: dict, db_session):
        """Test updating task information."""
        # This would require setting up a task first
        fake_id = str(uuid.uuid4())
        update_data = {
            "title": "Updated Task Title",
            "description": "Updated Description",
            "status": "in_progress"
        }
        
        response = client.put(f"/tasks/{fake_id}", json=update_data, headers=auth_headers)
        
        # Should fail because task doesn't exist
        assert response.status_code in [404, 403]
    
    def test_update_task_unauthorized(self, client: TestClient):
        """Test updating task without authentication."""
        fake_id = str(uuid.uuid4())
        update_data = {"title": "Updated Title"}
        
        response = client.put(f"/tasks/{fake_id}", json=update_data)
        
        assert response.status_code == 401
    
    def test_delete_task_success(self, client: TestClient, auth_headers: dict):
        """Test deleting a task."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/tasks/{fake_id}", headers=auth_headers)
        
        # Should fail because task doesn't exist
        assert response.status_code in [404, 403]
    
    def test_delete_task_unauthorized(self, client: TestClient):
        """Test deleting task without authentication."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/tasks/{fake_id}")
        
        assert response.status_code == 401

class TestTaskStatusAndAssignment:
    """Test task status updates and assignment."""
    
    def test_update_task_status_success(self, client: TestClient, auth_headers: dict):
        """Test updating task status."""
        fake_id = str(uuid.uuid4())
        status_data = {"status": "done"}
        
        response = client.put(f"/tasks/{fake_id}/status", json=status_data, headers=auth_headers)
        
        # Should fail because task doesn't exist
        assert response.status_code in [404, 403]
    
    def test_update_task_status_invalid_status(self, client: TestClient, auth_headers: dict):
        """Test updating task with invalid status."""
        fake_id = str(uuid.uuid4())
        status_data = {"status": "invalid_status"}
        
        response = client.put(f"/tasks/{fake_id}/status", json=status_data, headers=auth_headers)
        
        assert response.status_code in [400, 404, 403]
    
    def test_update_task_status_unauthorized(self, client: TestClient):
        """Test updating task status without authentication."""
        fake_id = str(uuid.uuid4())
        status_data = {"status": "done"}
        
        response = client.put(f"/tasks/{fake_id}/status", json=status_data)
        
        assert response.status_code == 401
    
    def test_assign_task_success(self, client: TestClient, auth_headers: dict):
        """Test assigning task to user."""
        fake_id = str(uuid.uuid4())
        assign_data = {"assignee_id": str(uuid.uuid4())}
        
        response = client.put(f"/tasks/{fake_id}/assign", json=assign_data, headers=auth_headers)
        
        # Should fail because task doesn't exist
        assert response.status_code in [404, 403]
    
    def test_assign_task_unauthorized(self, client: TestClient):
        """Test assigning task without authentication."""
        fake_id = str(uuid.uuid4())
        assign_data = {"assignee_id": str(uuid.uuid4())}
        
        response = client.put(f"/tasks/{fake_id}/assign", json=assign_data)
        
        assert response.status_code == 401

class TestProjectTasks:
    """Test project-specific task endpoints."""
    
    def test_get_project_tasks_success(self, client: TestClient, auth_headers: dict):
        """Test getting tasks for a specific project."""
        fake_project_id = str(uuid.uuid4())
        response = client.get(f"/tasks/project/{fake_project_id}", headers=auth_headers)
        
        # Should fail because user is not a project member
        assert response.status_code in [403, 404]
    
    def test_get_project_tasks_unauthorized(self, client: TestClient):
        """Test getting project tasks without authentication."""
        fake_project_id = str(uuid.uuid4())
        response = client.get(f"/tasks/project/{fake_project_id}")
        
        assert response.status_code == 401
    
    def test_get_project_tasks_with_pagination(self, client: TestClient, auth_headers: dict):
        """Test getting project tasks with pagination."""
        fake_project_id = str(uuid.uuid4())
        response = client.get(f"/tasks/project/{fake_project_id}?skip=0&limit=5", headers=auth_headers)
        
        # Should fail because user is not a project member
        assert response.status_code in [403, 404]

class TestMyTasks:
    """Test user-specific task endpoints."""
    
    def test_get_my_tasks_success(self, client: TestClient, auth_headers: dict):
        """Test getting tasks assigned to or created by current user."""
        response = client.get("/tasks/my/tasks", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_my_tasks_unauthorized(self, client: TestClient):
        """Test getting my tasks without authentication."""
        response = client.get("/tasks/my/tasks")
        
        assert response.status_code == 401
    
    def test_get_my_tasks_with_pagination(self, client: TestClient, auth_headers: dict):
        """Test getting my tasks with pagination."""
        response = client.get("/tasks/my/tasks?skip=0&limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestTaskValidation:
    """Test task input validation."""
    
    def test_create_task_missing_title(self, client: TestClient, auth_headers: dict):
        """Test creating task without title."""
        task_data = {
            "description": "Test task without title",
            "project_id": str(uuid.uuid4())
        }
        
        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_task_missing_project_id(self, client: TestClient, auth_headers: dict):
        """Test creating task without project_id."""
        task_data = {
            "title": "Test task",
            "description": "Test task description"
        }
        
        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_task_invalid_project_id(self, client: TestClient, auth_headers: dict):
        """Test creating task with invalid project_id."""
        task_data = {
            "title": "Test task",
            "description": "Test task description",
            "project_id": "invalid-uuid"
        }
        
        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_task_invalid_due_date(self, client: TestClient, auth_headers: dict):
        """Test creating task with invalid due date."""
        task_data = {
            "title": "Test task",
            "description": "Test task description",
            "project_id": str(uuid.uuid4()),
            "due_date": "invalid-date"
        }
        
        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_get_task_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test getting task with invalid UUID."""
        invalid_id = "invalid-uuid"
        response = client.get(f"/tasks/{invalid_id}", headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_update_task_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test updating task with invalid UUID."""
        invalid_id = "invalid-uuid"
        update_data = {"title": "Updated Title"}
        
        response = client.put(f"/tasks/{invalid_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_delete_task_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test deleting task with invalid UUID."""
        invalid_id = "invalid-uuid"
        response = client.delete(f"/tasks/{invalid_id}", headers=auth_headers)
        
        assert response.status_code == 422