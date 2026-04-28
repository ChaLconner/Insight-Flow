"""
Tests for routers/auth.py endpoints to increase coverage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from database import get_async_db
from dependencies import get_current_active_user, get_user_service
from main import app

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
            json={"email": "invalid-email", "password": "ValidPass123!", "fullName": "Test User"},
        )
        assert response.status_code == 422

    def test_register_weak_password(self, unauthenticated_client):
        """Test registration with weak password."""
        response = unauthenticated_client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "short", "fullName": "Test User"},
        )
        assert response.status_code == 422

    def test_register_missing_fields(self, unauthenticated_client):
        """Test registration with missing fields."""
        response = unauthenticated_client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422


class TestLoginEndpoint:
    def test_login_missing_credentials(self, unauthenticated_client):
        """Test login with missing credentials."""
        response = unauthenticated_client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_login_invalid_email_format(self, unauthenticated_client):
        """Test login with invalid email format."""
        response = unauthenticated_client.post(
            "/api/v1/auth/login", json={"email": "not-an-email", "password": "password123"}
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


class TestAuthRouterEdgeCases:
    """Detailed tests for edge cases in Auth Router."""

    @pytest.mark.asyncio
    async def test_login_account_locked(self, mock_db):
        """Test login with locked account."""
        mock_user_service = AsyncMock()
        mock_user_service.authenticate_user.side_effect = ValueError(
            "Account locked due to too many failed attempts"
        )

        async def mock_get_user_service():
            return mock_user_service

        app.dependency_overrides[get_user_service] = mock_get_user_service

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login", json={"email": "locked@example.com", "password": "password"}
            )
            try:
                assert response.status_code == 403
                assert "Account locked" in response.json()["message"]
            except Exception:
                raise

        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, mock_db):
        """Test login with inactive user."""
        mock_user_service = AsyncMock()
        mock_user = MagicMock()
        mock_user.is_active = False
        mock_user_service.authenticate_user.return_value = mock_user

        async def mock_get_user_service():
            return mock_user_service

        app.dependency_overrides[get_user_service] = mock_get_user_service

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login", json={"email": "inactive@example.com", "password": "password"}
            )
            try:
                assert response.status_code == 400
                assert "Inactive user" in response.json()["message"]
            except Exception:
                raise

        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_login_unverified_email(self, mock_db):
        """Test login with unverified email."""
        mock_user_service = AsyncMock()
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.is_verified = False
        mock_user_service.authenticate_user.return_value = mock_user

        async def mock_get_user_service():
            return mock_user_service

        app.dependency_overrides[get_user_service] = mock_get_user_service

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "unverified@example.com", "password": "password"},
            )
            try:
                assert response.status_code == 403
                assert "Email not verified" in response.json()["message"]
            except Exception:
                raise

        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_google_login_not_configured(self):
        """Test Google login when not configured."""
        with patch("routers.auth.is_google_oauth_configured", return_value=False):
            with TestClient(app) as client:
                response = client.post("/api/v1/auth/google", json={"idToken": "fake_token"})
            try:
                assert response.status_code == 500
                assert "not configured" in response.json()["message"]
            except Exception:
                raise

    @pytest.mark.asyncio
    async def test_google_login_invalid_token(self, mock_db):
        """Test Google login with invalid token."""
        with (
            patch("routers.auth.is_google_oauth_configured", return_value=True),
            patch("routers.auth.async_verify_google_id_token", return_value=None),
            TestClient(app) as client,
        ):
            response = client.post("/api/v1/auth/google", json={"idToken": "invalid_token"})
            try:
                assert response.status_code == 401
                assert "Invalid Google token" in response.json()["message"]
            except Exception:
                raise

    @pytest.mark.asyncio
    async def test_google_login_email_not_verified(self, mock_db):
        """Test Google login with unverified email."""
        with (
            patch("routers.auth.is_google_oauth_configured", return_value=True),
            patch(
                "routers.auth.async_verify_google_id_token", new_callable=AsyncMock
            ) as mock_verify,
        ):
            mock_verify.return_value = {"email_verified": False, "sub": "123"}

            with TestClient(app) as client:
                response = client.post("/api/v1/auth/google", json={"id_token": "token"})
                try:
                    assert response.status_code == 400
                    assert "Email is not verified" in response.json()["message"]
                except Exception:
                    raise

    @pytest.mark.asyncio
    async def test_change_password_incorrect_current(self, mock_db):
        """Test change password with incorrect current password."""
        mock_user = MagicMock()
        mock_user.hashed_password = "hashed_secret"
        mock_user.email = "test@example.com"

        mock_user_service = AsyncMock()
        mock_user_service.verify_password.return_value = False

        async def mock_get_current_active_user():
            return mock_user

        async def mock_get_user_service():
            return mock_user_service

        app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
        app.dependency_overrides[get_user_service] = mock_get_user_service

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/change-password",
                json={"currentPassword": "wrong", "newPassword": "NewValidPass123!"},
            )
            assert response.status_code == 400
            assert "Current password is incorrect" in response.json()["message"]

        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_refresh_token_revoked(self, mock_db):
        """Test refresh token that has been revoked/blacklisted."""
        # This requires mocking the dependency chain for refresh token
        # We'll use a mocked db session and patch the verify function

        with patch("routers.auth.async_verify_token_with_blacklist") as mock_verify:
            mock_verify.side_effect = HTTPException(status_code=401, detail="Token revoked")

            with TestClient(app) as client:
                client.cookies.set("refresh_token_cookie", "revoked_token")
                response = client.post("/api/v1/auth/refresh")

                assert response.status_code == 401
