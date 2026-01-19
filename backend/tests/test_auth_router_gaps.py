"""
Tests for Auth Router coverage gaps.
Focuses on missing paths in login/logout.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from routers.auth import login, logout


class TestAuthRouterGaps:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user_service(self):
        return AsyncMock()

    @pytest.fixture
    def mock_response(self):
        return MagicMock()

    @pytest.fixture
    def mock_request(self):
        req = MagicMock(spec=Request)
        req.client.host = "127.0.0.1"
        req.headers = {"user-agent": "TestBot"}
        req.cookies = {}
        return req

    @pytest.mark.asyncio
    async def test_login_success_full_flow(
        self, mock_db, mock_user_service, mock_response, mock_request
    ):
        """Test full login success flow including update_last_login and cookies."""
        from schemas.user import UserLogin

        login_data = UserLogin(email="test@example.com", password="password")

        mock_user = MagicMock()
        mock_user.id = "user_id_123"
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.name = "Test User"
        mock_user.avatar_url = "http://avatar"
        mock_user.role = "admin"  # Explicit role

        mock_user_service.authenticate_user.return_value = mock_user

        with patch("routers.auth.create_and_set_auth_cookies") as mock_set_cookies:
            result = await login(login_data, mock_response, mock_request, mock_user_service)

            # Verify update_last_login called
            mock_user_service.update_last_login.assert_called_with("user_id_123")

            # Verify cookies set
            mock_set_cookies.assert_called_once()

            # Verify response structure
            assert result["message"] == "Login successful"
            assert result["user"]["role"] == "admin"

    @pytest.mark.asyncio
    async def test_logout_with_jti_blacklisting(self, mock_db, mock_response, mock_request):
        """Test logout logic where token is verified and blacklisted."""
        mock_request.cookies = {"access_token": "valid.token.here"}

        with (
            patch("routers.auth.clear_auth_cookies") as mock_clear,
            # Patch utils.auth.verify_token because it is imported inside the function
            patch("utils.auth.verify_token") as mock_verify,
        ):
            mock_verify.return_value = {"jti": "unique_id", "sub": "user_123"}

            with patch("routers.auth.get_token_expiration") as mock_exp:
                mock_exp.return_value = 1000

                # Also patch token blacklist
                with patch("routers.auth.TokenBlacklist.async_blacklist_token") as mock_bl:
                    mock_bl.return_value = None

                    result = await logout(mock_request, mock_response, db=mock_db)

                    assert result["message"] == "Successfully logged out"
                    mock_clear.assert_called_once()
                    mock_bl.assert_called_once()
