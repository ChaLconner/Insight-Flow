"""
Authentication endpoint tests.
"""
import pytest
from fastapi.testclient import TestClient
from httpx import Response

class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_register_success(self, client: TestClient, test_user_data: dict):
        """Test successful user registration."""
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["name"] == test_user_data["name"]
        assert "id" in data
        assert "password" not in data
    
    def test_register_duplicate_email(self, client: TestClient, test_user: dict):
        """Test registration with duplicate email."""
        user_data = {
            "email": "test@example.com",
            "name": "Another User",
            "password": "password123"
        }
        
        response = client.post("/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email."""
        user_data = {
            "email": "invalid-email",
            "name": "Test User",
            "password": "password123"
        }
        
        response = client.post("/auth/register", json=user_data)
        
        assert response.status_code == 422
    
    def test_register_missing_password(self, client: TestClient):
        """Test registration without password."""
        user_data = {
            "email": "test@example.com",
            "name": "Test User"
        }
        
        response = client.post("/auth/register", json=user_data)
        
        assert response.status_code == 422
    
    def test_login_success(self, client: TestClient, test_user_data: dict):
        """Test successful login."""
        # First register the user
        client.post("/auth/register", json=test_user_data)
        
        # Then login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)
    
    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_missing_fields(self, client: TestClient):
        """Test login with missing fields."""
        login_data = {
            "email": "test@example.com"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 422
    
    def test_get_current_user(self, client: TestClient, auth_headers: dict, test_user: dict):
        """Test getting current user info."""
        response = client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert data["id"] == str(test_user.id)
    
    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_refresh_token_success(self, client: TestClient, auth_headers: dict):
        """Test successful token refresh."""
        response = client.post("/auth/refresh", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_refresh_token_unauthorized(self, client: TestClient):
        """Test token refresh without authentication."""
        response = client.post("/auth/refresh")
        
        assert response.status_code == 401
    
    def test_google_oauth_missing_id_token(self, client: TestClient):
        """Test Google OAuth without ID token."""
        response = client.post("/auth/google", json={})
        
        assert response.status_code == 422
    
    def test_google_oauth_with_id_token(self, client: TestClient):
        """Test Google OAuth with ID token (mock)."""
        # This would require mocking Google's verification service
        oauth_data = {
            "id_token": "mock_google_id_token"
        }
        
        response = client.post("/auth/google", json=oauth_data)
        
        # Should fail with invalid token, but not with validation error
        assert response.status_code in [400, 401]

class TestTokenValidation:
    """Test token validation and security."""
    
    def test_expired_token(self, client: TestClient):
        """Test access with expired token."""
        # This would require creating an expired token
        import jwt
        from datetime import datetime, timedelta
        
        expired_token = jwt.encode(
            {
                "sub": "test_user_id",
                "exp": datetime.utcnow() - timedelta(hours=1),
                "iat": datetime.utcnow() - timedelta(hours=2)
            },
            "secret_key",  # This should match your actual secret
            algorithm="HS256"
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_malformed_token(self, client: TestClient):
        """Test access with malformed token."""
        headers = {"Authorization": "Bearer malformed.jwt.token"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_missing_token_header(self, client: TestClient):
        """Test access without Authorization header."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_invalid_bearer_format(self, client: TestClient):
        """Test access with invalid Authorization header format."""
        headers = {"Authorization": "InvalidFormat token"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401