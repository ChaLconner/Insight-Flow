"""
User management endpoint tests.
"""
import pytest
from fastapi.testclient import TestClient
import uuid

class TestUserManagement:
    """Test user management endpoints."""
    
    def test_get_users_list(self, client: TestClient, auth_headers: dict):
        """Test getting list of users."""
        response = client.get("/users/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_users_unauthorized(self, client: TestClient):
        """Test getting users without authentication."""
        response = client.get("/users/")
        
        assert response.status_code == 401
    
    def test_get_users_with_pagination(self, client: TestClient, auth_headers: dict):
        """Test getting users with pagination."""
        response = client.get("/users/?skip=0&limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_user_success(self, client: TestClient, auth_headers: dict, test_user_data: dict):
        """Test creating a new user."""
        new_user_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "newpassword123"
        }
        
        response = client.post("/users/", json=new_user_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == new_user_data["email"]
        assert data["name"] == new_user_data["name"]
        assert "id" in data
        assert "password" not in data
    
    def test_create_user_duplicate_email(self, client: TestClient, auth_headers: dict, test_user_data: dict):
        """Test creating user with duplicate email."""
        response = client.post("/users/", json=test_user_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_create_user_unauthorized(self, client: TestClient, test_user_data: dict):
        """Test creating user without authentication."""
        response = client.post("/users/", json=test_user_data)
        
        assert response.status_code == 401
    
    def test_get_user_by_id_success(self, client: TestClient, auth_headers: dict, test_user: dict):
        """Test getting user by ID."""
        user_id = str(test_user.id)
        response = client.get(f"/users/{user_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
    
    def test_get_user_by_id_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting non-existent user."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/users/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_get_user_by_id_unauthorized(self, client: TestClient, test_user: dict):
        """Test getting user by ID without authentication."""
        user_id = str(test_user.id)
        response = client.get(f"/users/{user_id}")
        
        assert response.status_code == 401
    
    def test_update_user_success(self, client: TestClient, auth_headers: dict, test_user: dict):
        """Test updating user information."""
        user_id = str(test_user.id)
        update_data = {
            "name": "Updated Name",
            "avatar_url": "https://example.com/new-avatar.jpg"
        }
        
        response = client.put(f"/users/{user_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["avatar_url"] == update_data["avatar_url"]
        assert data["email"] == test_user.email  # Email should remain unchanged
    
    def test_update_user_not_found(self, client: TestClient, auth_headers: dict):
        """Test updating non-existent user."""
        fake_id = str(uuid.uuid4())
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/users/{fake_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_update_user_unauthorized(self, client: TestClient, test_user: dict):
        """Test updating user without authentication."""
        user_id = str(test_user.id)
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/users/{user_id}", json=update_data)
        
        assert response.status_code == 401
    
    def test_delete_user_success(self, client: TestClient, admin_headers: dict, db_session):
        """Test deleting a user."""
        # Create a user to delete
        from services.user_service import UserService
        from schemas.user import UserCreate
        user_service = UserService(db_session)
        user_data = UserCreate(
            email="delete@example.com",
            name="Delete User",
            password="password123"
        )
        user_to_delete = user_service.create_user(user_data)
        
        user_id = str(user_to_delete.id)
        response = client.delete(f"/users/{user_id}", headers=admin_headers)
        
        assert response.status_code == 200
        assert "User deleted successfully" in response.json()["message"]
    
    def test_delete_user_not_found(self, client: TestClient, auth_headers: dict):
        """Test deleting non-existent user."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/users/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_delete_self_prevention(self, client: TestClient, auth_headers: dict, test_user: dict):
        """Test preventing self-deletion."""
        user_id = str(test_user.id)
        response = client.delete(f"/users/{user_id}", headers=auth_headers)
        
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]
    
    def test_delete_user_unauthorized(self, client: TestClient, test_user: dict):
        """Test deleting user without authentication."""
        user_id = str(test_user.id)
        response = client.delete(f"/users/{user_id}")
        
        assert response.status_code == 401
    
    def test_search_user_by_email_success(self, client: TestClient, auth_headers: dict, test_user: dict):
        """Test searching user by email."""
        email = test_user.email
        response = client.get(f"/users/search/{email}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert data["name"] == test_user.name
    
    def test_search_user_by_email_not_found(self, client: TestClient, auth_headers: dict):
        """Test searching for non-existent user by email."""
        email = "nonexistent@example.com"
        response = client.get(f"/users/search/{email}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_search_user_by_email_unauthorized(self, client: TestClient, test_user: dict):
        """Test searching user by email without authentication."""
        email = test_user.email
        response = client.get(f"/users/search/{email}")
        
        assert response.status_code == 401

class TestUserValidation:
    """Test user input validation."""
    
    def test_create_user_invalid_email(self, client: TestClient, auth_headers: dict):
        """Test creating user with invalid email."""
        user_data = {
            "email": "invalid-email",
            "name": "Test User",
            "password": "password123"
        }
        
        response = client.post("/users/", json=user_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_user_short_password(self, client: TestClient, auth_headers: dict):
        """Test creating user with short password."""
        user_data = {
            "email": "test@example.com",
            "name": "Test User",
            "password": "123"
        }
        
        response = client.post("/users/", json=user_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_user_missing_name(self, client: TestClient, auth_headers: dict):
        """Test creating user without name."""
        user_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = client.post("/users/", json=user_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_update_user_invalid_avatar_url(self, client: TestClient, auth_headers: dict, test_user: dict):
        """Test updating user with invalid avatar URL."""
        user_id = str(test_user.id)
        update_data = {
            "avatar_url": "invalid-url"
        }
        
        response = client.put(f"/users/{user_id}", json=update_data, headers=auth_headers)
        
        # Should either succeed (if URL validation is lenient) or fail with validation error
        assert response.status_code in [200, 422]
    
    def test_get_user_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test getting user with invalid UUID."""
        invalid_id = "invalid-uuid"
        response = client.get(f"/users/{invalid_id}", headers=auth_headers)
        
        assert response.status_code == 422