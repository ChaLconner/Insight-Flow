"""
Tests for routers/auth.py endpoints to increase coverage.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from main import app
from database import get_async_db
from routers.auth import get_current_active_user
from models.user import User


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock async database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def unauthenticated_client(mock_db):
    """Test client without authentication."""
    async def override_get_async_db():
        yield mock_db
    
    app.dependency_overrides[get_async_db] = override_get_async_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides = {}


# ============================================================================
# Tests for Auth Endpoints
# ============================================================================

class TestRegisterEndpoint:
    def test_register_invalid_email(self, unauthenticated_client):
        """Test registration with invalid email."""
        response = unauthenticated_client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "ValidPass123!",
                "fullName": "Test User"
            }
        )
        assert response.status_code == 422

    def test_register_weak_password(self, unauthenticated_client):
        """Test registration with weak password."""
        response = unauthenticated_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
                "fullName": "Test User"
            }
        )
        assert response.status_code == 422

    def test_register_missing_fields(self, unauthenticated_client):
        """Test registration with missing fields."""
        response = unauthenticated_client.post(
            "/api/v1/auth/register",
            json={}
        )
        assert response.status_code == 422


class TestLoginEndpoint:
    def test_login_missing_credentials(self, unauthenticated_client):
        """Test login with missing credentials."""
        response = unauthenticated_client.post(
            "/api/v1/auth/login",
            json={}
        )
        assert response.status_code == 422

    def test_login_invalid_email_format(self, unauthenticated_client):
        """Test login with invalid email format."""
        response = unauthenticated_client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "password123"
            }
        )
        assert response.status_code == 422


class TestMeEndpoint:
    def test_me_unauthenticated(self, unauthenticated_client):
        """Test getting current user when not authenticated."""
        response = unauthenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestLogoutEndpoint:
    def test_logout_unauthenticated(self, unauthenticated_client):
        """Test logout clears cookies even when not logged in."""
        response = unauthenticated_client.post("/api/v1/auth/logout")
        # Logout typically returns 200 even without auth (just clears cookies)
        assert response.status_code in [200, 401]


class TestRefreshTokenEndpoint:
    def test_refresh_no_token(self, unauthenticated_client):
        """Test refresh without token."""
        response = unauthenticated_client.post("/api/v1/auth/refresh")
        assert response.status_code in [401, 400, 422]
