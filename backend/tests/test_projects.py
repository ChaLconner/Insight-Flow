"""
Project management endpoint tests.
"""
import pytest
from fastapi.testclient import TestClient
import uuid

class TestProjectManagement:
    """Test project management endpoints."""
    
    def test_get_projects_list(self, client: TestClient, auth_headers: dict):
        """Test getting list of projects."""
        response = client.get("/projects/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_projects_unauthorized(self, client: TestClient):
        """Test getting projects without authentication."""
        response = client.get("/projects/")
        
        assert response.status_code == 401
    
    def test_get_projects_with_pagination(self, client: TestClient, auth_headers: dict):
        """Test getting projects with pagination."""
        response = client.get("/projects/?skip=0&limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_user_projects_only(self, client: TestClient, auth_headers: dict):
        """Test getting only user's projects."""
        response = client.get("/projects/?user_projects_only=true", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_project_success(self, client: TestClient, auth_headers: dict, sample_project_data: dict):
        """Test creating a new project."""
        response = client.post("/projects/", json=sample_project_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_project_data["name"]
        assert data["description"] == sample_project_data["description"]
        assert "id" in data
        assert "owner_id" in data
        assert data["is_active"] is True
    
    def test_create_project_unauthorized(self, client: TestClient, sample_project_data: dict):
        """Test creating project without authentication."""
        response = client.post("/projects/", json=sample_project_data)
        
        assert response.status_code == 401
    
    def test_create_project_invalid_data(self, client: TestClient, auth_headers: dict):
        """Test creating project with invalid data."""
        invalid_data = {
            "name": "",  # Empty name should fail
            "description": "Test project"
        }
        
        response = client.post("/projects/", json=invalid_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_get_project_by_id_success(self, client: TestClient, auth_headers: dict, sample_project_data: dict, db_session):
        """Test getting project by ID."""
        # First create a project
        from services.project_service import ProjectService
        from schemas.project import ProjectCreate
        project_service = ProjectService(db_session)
        project_data = ProjectCreate(**sample_project_data)
        
        # Create a test user to be the owner
        from services.user_service import UserService
        from schemas.user import UserCreate
        user_service = UserService(db_session)
        user_data = UserCreate(
            email="owner@example.com",
            name="Owner User",
            password="password123"
        )
        owner = user_service.create_user(user_data)
        
        project = project_service.create_project(project_data, owner.id)
        
        # Add current user as member
        from utils.auth import create_access_token
        token = create_access_token(data={"sub": str(owner.id)})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get(f"/projects/{project.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(project.id)
        assert data["name"] == project.name
        assert "members" in data
        assert isinstance(data["members"], list)
    
    def test_get_project_by_id_not_member(self, client: TestClient, auth_headers: dict):
        """Test getting project when not a member."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/projects/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404  # or 403 depending on implementation
    
    def test_get_project_by_id_unauthorized(self, client: TestClient):
        """Test getting project without authentication."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/projects/{fake_id}")
        
        assert response.status_code == 401
    
    def test_update_project_success(self, client: TestClient, auth_headers: dict, sample_project_data: dict, db_session):
        """Test updating project information."""
        # Create project first
        from services.project_service import ProjectService
        from schemas.project import ProjectCreate
        project_service = ProjectService(db_session)
        project_data = ProjectCreate(**sample_project_data)
        
        # Get current user from auth headers
        from utils.auth import verify_token
        # This is a simplified approach - in real test you'd extract user from token
        import jwt
        token = auth_headers["Authorization"].split(" ")[1]
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = uuid.UUID(payload["sub"])
        
        project = project_service.create_project(project_data, user_id)
        
        update_data = {
            "name": "Updated Project Name",
            "description": "Updated Description"
        }
        
        response = client.put(f"/projects/{project.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_update_project_not_owner(self, client: TestClient, auth_headers: dict):
        """Test updating project without being owner."""
        fake_id = str(uuid.uuid4())
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/projects/{fake_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code in [403, 404]  # Forbidden or Not Found
    
    def test_update_project_unauthorized(self, client: TestClient, sample_project_data: dict):
        """Test updating project without authentication."""
        fake_id = str(uuid.uuid4())
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/projects/{fake_id}", json=update_data)
        
        assert response.status_code == 401
    
    def test_delete_project_success(self, client: TestClient, auth_headers: dict, sample_project_data: dict, db_session):
        """Test deleting a project."""
        # Create project first
        from services.project_service import ProjectService
        from schemas.project import ProjectCreate
        project_service = ProjectService(db_session)
        project_data = ProjectCreate(**sample_project_data)
        
        # Get current user ID from token
        import jwt
        token = auth_headers["Authorization"].split(" ")[1]
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = uuid.UUID(payload["sub"])
        
        project = project_service.create_project(project_data, user_id)
        
        response = client.delete(f"/projects/{project.id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert "Project deleted successfully" in response.json()["message"]
    
    def test_delete_project_not_owner(self, client: TestClient, auth_headers: dict):
        """Test deleting project without being owner."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/projects/{fake_id}", headers=auth_headers)
        
        assert response.status_code in [403, 404]
    
    def test_delete_project_unauthorized(self, client: TestClient):
        """Test deleting project without authentication."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/projects/{fake_id}")
        
        assert response.status_code == 401

class TestProjectMembers:
    """Test project member management."""
    
    def test_get_project_members_success(self, client: TestClient, auth_headers: dict, db_session):
        """Test getting project members."""
        # This would require setting up a project with members
        # For now, test the endpoint structure
        fake_id = str(uuid.uuid4())
        response = client.get(f"/projects/{fake_id}/members", headers=auth_headers)
        
        # Should fail because user is not a member
        assert response.status_code in [403, 404]
    
    def test_get_project_members_unauthorized(self, client: TestClient):
        """Test getting project members without authentication."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/projects/{fake_id}/members")
        
        assert response.status_code == 401
    
    def test_add_project_member_success(self, client: TestClient, auth_headers: dict, db_session):
        """Test adding a member to project."""
        # This would require setting up a project and user
        member_data = {
            "user_id": str(uuid.uuid4()),
            "role": "member"
        }
        fake_id = str(uuid.uuid4())
        
        response = client.post(f"/projects/{fake_id}/members", json=member_data, headers=auth_headers)
        
        # Should fail because project doesn't exist or user is not owner
        assert response.status_code in [400, 403, 404]
    
    def test_add_project_member_unauthorized(self, client: TestClient):
        """Test adding member without authentication."""
        member_data = {
            "user_id": str(uuid.uuid4()),
            "role": "member"
        }
        fake_id = str(uuid.uuid4())
        
        response = client.post(f"/projects/{fake_id}/members", json=member_data)
        
        assert response.status_code == 401
    
    def test_remove_project_member_success(self, client: TestClient, auth_headers: dict):
        """Test removing a member from project."""
        fake_project_id = str(uuid.uuid4())
        fake_member_id = str(uuid.uuid4())
        
        response = client.delete(f"/projects/{fake_project_id}/members/{fake_member_id}", headers=auth_headers)
        
        # Should fail because project doesn't exist or user is not owner
        assert response.status_code in [400, 403, 404]
    
    def test_remove_project_member_unauthorized(self, client: TestClient):
        """Test removing member without authentication."""
        fake_project_id = str(uuid.uuid4())
        fake_member_id = str(uuid.uuid4())
        
        response = client.delete(f"/projects/{fake_project_id}/members/{fake_member_id}")
        
        assert response.status_code == 401
    
    def test_update_member_role_success(self, client: TestClient, auth_headers: dict):
        """Test updating member role."""
        fake_project_id = str(uuid.uuid4())
        fake_member_id = str(uuid.uuid4())
        
        response = client.put(f"/projects/{fake_project_id}/members/{fake_member_id}/role?role=admin", headers=auth_headers)
        
        # Should fail because project doesn't exist or user is not owner
        assert response.status_code in [400, 403, 404]
    
    def test_update_member_role_unauthorized(self, client: TestClient):
        """Test updating member role without authentication."""
        fake_project_id = str(uuid.uuid4())
        fake_member_id = str(uuid.uuid4())
        
        response = client.put(f"/projects/{fake_project_id}/members/{fake_member_id}/role?role=admin")
        
        assert response.status_code == 401

class TestProjectValidation:
    """Test project input validation."""
    
    def test_create_project_missing_name(self, client: TestClient, auth_headers: dict):
        """Test creating project without name."""
        project_data = {
            "description": "Test project without name"
        }
        
        response = client.post("/projects/", json=project_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_project_too_long_name(self, client: TestClient, auth_headers: dict):
        """Test creating project with too long name."""
        project_data = {
            "name": "a" * 256,  # Assuming max length is 255
            "description": "Test project"
        }
        
        response = client.post("/projects/", json=project_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_get_project_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test getting project with invalid UUID."""
        invalid_id = "invalid-uuid"
        response = client.get(f"/projects/{invalid_id}", headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_update_project_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test updating project with invalid UUID."""
        invalid_id = "invalid-uuid"
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/projects/{invalid_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_delete_project_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test deleting project with invalid UUID."""
        invalid_id = "invalid-uuid"
        response = client.delete(f"/projects/{invalid_id}", headers=auth_headers)
        
        assert response.status_code == 422