"""
Tests for routers/auth.py endpoints.

Uses mocked dependencies for isolated testing.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from main import app
from dependencies import get_user_service, get_password_reset_service
from dependencies.auth import get_current_user
from routers.auth import get_current_active_user
from database import get_async_db
from models.user import User


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_user_service():
    """Mock AsyncUserService."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_password_reset_service():
    """Mock AsyncPasswordResetService."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_db():
    """Mock async database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_current_user():
    """Mock User model."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.username = "testuser"
    user.name = "Test User"
    user.avatar_url = None
    user.role = "user"
    user.is_active = True
    user.is_verified = True
    user.hashed_password = "hashedpassword123"
    return user


@pytest.fixture
def authenticated_client(mock_user_service, mock_password_reset_service, mock_db, mock_current_user):
    """Test client with authenticated user."""
    async def override_get_async_db():
        yield mock_db
    
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_password_reset_service] = lambda: mock_password_reset_service
    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_current_active_user] = lambda: mock_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides = {}


@pytest.fixture
def unauthenticated_client(mock_user_service, mock_password_reset_service, mock_db):
    """Test client without authentication."""
    async def override_get_async_db():
        yield mock_db
    
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_password_reset_service] = lambda: mock_password_reset_service
    app.dependency_overrides[get_async_db] = override_get_async_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides = {}


# ============================================================================
# Tests for Login
# ============================================================================

class TestLogin:
    def test_login_missing_credentials(self, unauthenticated_client):
        """Test login fails with missing credentials."""
        response = unauthenticated_client.post(
            "/api/v1/auth/login",
            json={}
        )
        assert response.status_code == 422
    
    def test_login_invalid_credentials(self, unauthenticated_client, mock_user_service):
        """Test login fails with invalid credentials."""
        mock_user_service.authenticate_user.return_value = None
        
        response = unauthenticated_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401


# ============================================================================
# Tests for Me Endpoint
# ============================================================================

class TestMeEndpoint:
    def test_me_unauthenticated(self, unauthenticated_client):
        """Test /me endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 401


# ============================================================================
# Tests for Logout
# ============================================================================

class TestLogout:
    def test_logout_success(self, authenticated_client, mock_current_user):
        """Test logout clears cookies."""
        response = authenticated_client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"


# ============================================================================
# Tests for Password Reset
# ============================================================================

class TestPasswordReset:
    def test_forgot_password_success(self, unauthenticated_client, mock_password_reset_service):
        """Test forgot password sends email."""
        mock_token = MagicMock()
        mock_token.token = "resettoken123"
        mock_token.raw_token = "rawtoken123"
        mock_password_reset_service.create_password_reset_token.return_value = mock_token
        mock_password_reset_service.send_reset_email.return_value = True
        
        response = unauthenticated_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_forgot_password_nonexistent_email(self, unauthenticated_client, mock_password_reset_service):
        """Test forgot password for non-existent email."""
        mock_password_reset_service.create_password_reset_token.return_value = None
        
        response = unauthenticated_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )
        # Should still return success for security (don't reveal if email exists)
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_reset_password_invalid_token(self, unauthenticated_client, mock_password_reset_service):
        """Test reset password with invalid token."""
        mock_password_reset_service.reset_password.return_value = False
        
        response = unauthenticated_client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalidtoken",
                "new_password": "NewPass123!"
            }
        )
        assert response.status_code == 400
    
    def test_validate_reset_token_valid(self, unauthenticated_client, mock_password_reset_service):
        """Test validating a valid reset token."""
        mock_password_reset_service.validate_reset_token.return_value = MagicMock()
        
        response = unauthenticated_client.post(
            "/api/v1/auth/validate-reset-token",
            json={"token": "validtoken123"}
        )
        assert response.status_code == 200
        assert response.json()["valid"] is True
    
    def test_validate_reset_token_invalid(self, unauthenticated_client, mock_password_reset_service):
        """Test validating an invalid reset token."""
        mock_password_reset_service.validate_reset_token.return_value = None
        
        response = unauthenticated_client.post(
            "/api/v1/auth/validate-reset-token",
            json={"token": "invalidtoken"}
        )
        assert response.status_code == 200
        assert response.json()["valid"] is False


# ============================================================================
# Tests for Email Verification
# ============================================================================

class TestEmailVerification:
    def test_verify_email_invalid_token(self, unauthenticated_client, mock_user_service):
        """Test email verification with invalid token."""
        mock_user_service.verify_email.return_value = False
        
        response = unauthenticated_client.get(
            "/api/v1/auth/verify-email",
            params={"token": "invalidtoken"}
        )
        assert response.status_code == 400
    
    def test_verify_email_success(self, unauthenticated_client, mock_user_service):
        """Test email verification success."""
        mock_user_service.verify_email.return_value = True
        
        response = unauthenticated_client.get(
            "/api/v1/auth/verify-email",
            params={"token": "validtoken"}
        )
        assert response.status_code == 200
        assert "verified" in response.json()["message"]
