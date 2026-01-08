"""
Additional tests for auth router edge cases.
Covers missing paths in routers/auth.py for increased coverage.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestLoginEdgeCases:
    """Tests for login edge cases."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "TestAgent/1.0"}
        return request

    @pytest.fixture
    def mock_response(self):
        """Create a mock response."""
        return MagicMock()

    @pytest.fixture
    def mock_user_service(self):
        """Create a mock user service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_login_account_locked(self, mock_request, mock_response, mock_user_service):
        """Test that account lockout returns 403."""
        from routers.auth import login
        from schemas.user import UserLogin

        mock_user_service.authenticate_user = AsyncMock(
            side_effect=ValueError("Account locked until 2026-01-01")
        )

        login_data = UserLogin(email="locked@example.com", password="password123")

        with pytest.raises(HTTPException) as exc_info:
            await login(login_data, mock_response, mock_request, mock_user_service)

        assert exc_info.value.status_code == 403
        assert "Account locked" in exc_info.value.detail


class TestLogoutEdgeCases:
    """Tests for logout edge cases."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request with cookies."""
        request = MagicMock()
        request.cookies = {}
        request.headers = {}
        return request

    @pytest.fixture
    def mock_response(self):
        """Create a mock response."""
        return MagicMock()

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_logout_without_token(self, mock_request, mock_response, mock_db):
        """Test logout without any token."""
        from routers.auth import logout

        mock_request.cookies = {}
        mock_request.headers = {}

        with patch("routers.auth.clear_auth_cookies") as mock_clear:
            result = await logout(mock_request, mock_response, mock_db)

            assert result["message"] == "Successfully logged out"
            mock_clear.assert_called_once()


class TestRefreshTokenEdgeCases:
    """Tests for refresh token edge cases."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock()
        request.cookies = {}
        request.headers = {}
        return request

    @pytest.fixture
    def mock_response(self):
        """Create a mock response."""
        return MagicMock()

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_user_service(self):
        """Create a mock user service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_refresh_token_missing_returns_401(
        self, mock_request, mock_response, mock_db, mock_user_service
    ):
        """Test refresh token returns 401 when no token provided."""
        from routers.auth import refresh_token

        mock_request.cookies = {}
        mock_request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await refresh_token(mock_request, mock_response, mock_db, mock_user_service)

        assert exc_info.value.status_code == 401
        assert "null or empty" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found(
        self, mock_request, mock_response, mock_db, mock_user_service
    ):
        """Test refresh token returns 401 when user not found."""
        from routers.auth import refresh_token

        mock_request.cookies = {"refresh_token": "valid_refresh_token"}

        with patch(
            "routers.auth.async_verify_token_with_blacklist", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = {
                "sub": str(uuid.uuid4()),
                "jti": "token-jti",
            }

            mock_user_service.get_user_by_id = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await refresh_token(mock_request, mock_response, mock_db, mock_user_service)

            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_refresh_token_user_inactive(
        self, mock_request, mock_response, mock_db, mock_user_service
    ):
        """Test refresh token returns 400 for inactive user."""
        from routers.auth import refresh_token

        mock_request.cookies = {"refresh_token": "valid_refresh_token"}

        with patch(
            "routers.auth.async_verify_token_with_blacklist", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = {
                "sub": str(uuid.uuid4()),
                "jti": "token-jti",
            }

            mock_user = MagicMock()
            mock_user.is_active = False
            mock_user_service.get_user_by_id = AsyncMock(return_value=mock_user)

            with pytest.raises(HTTPException) as exc_info:
                await refresh_token(mock_request, mock_response, mock_db, mock_user_service)

            assert exc_info.value.status_code == 400
            assert "Inactive user" in exc_info.value.detail


class TestGoogleLoginEdgeCases:
    """Tests for Google login edge cases."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        return MagicMock()

    @pytest.fixture
    def mock_response(self):
        """Create a mock response."""
        return MagicMock()

    @pytest.fixture
    def mock_user_service(self):
        """Create a mock user service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_google_login_not_configured(
        self, mock_request, mock_response, mock_user_service
    ):
        """Test Google login returns 500 when not configured."""
        from routers.auth import google_login
        from schemas.user import GoogleAuth

        google_data = GoogleAuth(id_token="some_token")

        with patch("routers.auth.is_google_oauth_configured", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await google_login(mock_request, mock_response, google_data, mock_user_service)

            assert exc_info.value.status_code == 500
            assert "not configured" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_google_login_inactive_user(self, mock_request, mock_response, mock_user_service):
        """Test Google login returns 400 for inactive user."""
        from routers.auth import google_login
        from schemas.user import GoogleAuth

        google_data = GoogleAuth(id_token="valid_id_token")

        with patch("routers.auth.is_google_oauth_configured", return_value=True), patch(
            "routers.auth.async_verify_google_id_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = {
                "id": "google-123",
                "email": "test@gmail.com",
                "name": "Test User",
                "email_verified": True,
            }

            mock_user = MagicMock()
            mock_user.is_active = False
            mock_user_service.create_or_update_google_user = AsyncMock(return_value=mock_user)

            with pytest.raises(HTTPException) as exc_info:
                await google_login(mock_request, mock_response, google_data, mock_user_service)

            assert exc_info.value.status_code == 400


class TestGithubLoginEdgeCases:
    """Tests for GitHub login edge cases."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        return MagicMock()

    @pytest.fixture
    def mock_response(self):
        """Create a mock response."""
        return MagicMock()

    @pytest.fixture
    def mock_user_service(self):
        """Create a mock user service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_github_login_not_configured(
        self, mock_request, mock_response, mock_user_service
    ):
        """Test GitHub login returns 500 when not configured."""
        from routers.auth import github_login
        from schemas.user import GithubAuth

        github_data = GithubAuth(code="some_code")

        with patch("routers.auth.is_github_oauth_configured", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await github_login(mock_request, mock_response, github_data, mock_user_service)

            assert exc_info.value.status_code == 500
            assert "not configured" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_github_login_with_access_token(
        self, mock_request, mock_response, mock_user_service
    ):
        """Test GitHub login with direct access token."""
        from routers.auth import github_login
        from schemas.user import GithubAuth

        github_data = GithubAuth(access_token="github_access_token")

        with patch("routers.auth.is_github_oauth_configured", return_value=True), patch(
            "routers.auth.async_get_github_user_info", new_callable=AsyncMock
        ) as mock_user_info:
            mock_user_info.return_value = {
                "id": "github-123",
                "email": "test@github.com",
                "name": "GitHub User",
            }

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user.email = "test@github.com"
            mock_user.username = "githubuser"
            mock_user.name = "GitHub User"
            mock_user.avatar_url = None
            mock_user.role = "user"
            mock_user.is_active = True

            mock_user_service.create_or_update_github_user = AsyncMock(return_value=mock_user)
            mock_user_service.update_last_login = AsyncMock()

            with patch("routers.auth.create_and_set_auth_cookies"):
                result = await github_login(
                    mock_request, mock_response, github_data, mock_user_service
                )

                assert result["message"] == "Login successful"
                assert result["user"]["email"] == "test@github.com"

    @pytest.mark.asyncio
    async def test_github_login_inactive_user(self, mock_request, mock_response, mock_user_service):
        """Test GitHub login returns 400 for inactive user."""
        from routers.auth import github_login
        from schemas.user import GithubAuth

        github_data = GithubAuth(access_token="github_access_token")

        with patch("routers.auth.is_github_oauth_configured", return_value=True), patch(
            "routers.auth.async_get_github_user_info", new_callable=AsyncMock
        ) as mock_user_info:
            mock_user_info.return_value = {
                "id": "github-123",
                "email": "test@github.com",
                "name": "GitHub User",
            }

            mock_user = MagicMock()
            mock_user.is_active = False

            mock_user_service.create_or_update_github_user = AsyncMock(return_value=mock_user)

            with pytest.raises(HTTPException) as exc_info:
                await github_login(mock_request, mock_response, github_data, mock_user_service)

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_github_login_no_access_token(
        self, mock_request, mock_response, mock_user_service
    ):
        """Test GitHub login returns 401 when no token obtained."""
        from routers.auth import github_login
        from schemas.user import GithubAuth

        # Neither code nor access_token results in None
        github_data = GithubAuth()

        with patch("routers.auth.is_github_oauth_configured", return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                await github_login(mock_request, mock_response, github_data, mock_user_service)

            assert exc_info.value.status_code == 401
            assert "Failed to authenticate" in exc_info.value.detail


class TestVerifyEmailEndpoint:
    """Tests for verify email endpoint."""

    @pytest.fixture
    def mock_user_service(self):
        """Create a mock user service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_verify_email_success(self, mock_user_service):
        """Test successful email verification."""
        from routers.auth import verify_email

        mock_user_service.verify_email = AsyncMock(return_value=True)

        result = await verify_email("valid_token", mock_user_service)

        assert result["message"] == "Email verified successfully"

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, mock_user_service):
        """Test email verification with invalid token."""
        from routers.auth import verify_email

        mock_user_service.verify_email = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await verify_email("invalid_token", mock_user_service)

        assert exc_info.value.status_code == 400
        assert "Invalid or expired" in exc_info.value.detail


class TestResendVerificationEndpoint:
    """Tests for resend verification endpoint."""

    @pytest.fixture
    def mock_user_service(self):
        """Create a mock user service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_resend_verification_always_succeeds(self, mock_user_service):
        """Test resend verification always returns success message."""
        from routers.auth import resend_verification
        from schemas.user import ResendVerificationRequest

        mock_user_service.resend_verification_email = AsyncMock()

        request_data = ResendVerificationRequest(email="test@example.com")
        result = await resend_verification(request_data, mock_user_service)

        # Should always return success message for security
        assert "verification link" in result["message"]
