"""
Tests for utils/github_oauth.py with mocked external calls.

Focus on testable parts without complex httpx mocking.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGitHubOAuthConfiguration:
    """Tests for GitHub OAuth configuration checks."""

    def test_is_github_oauth_configured_function_exists(self):
        """Test is_github_oauth_configured function exists and returns bool."""
        from utils.github_oauth import is_github_oauth_configured

        result = is_github_oauth_configured()

        assert isinstance(result, bool)


class TestExchangeCodeForToken:
    """Tests for exchange_code_for_token function."""

    def test_exchange_code_no_credentials(self):
        """Test returns None when credentials not configured."""
        with (
            patch("utils.github_oauth.GITHUB_CLIENT_ID", None),
            patch("utils.github_oauth.GITHUB_CLIENT_SECRET", None),
        ):
            from utils.github_oauth import exchange_code_for_token

            result = exchange_code_for_token("test_code")

            assert result is None

    def test_exchange_code_success(self):
        """Test successful code exchange."""
        with (
            patch("utils.github_oauth.GITHUB_CLIENT_ID", "test_client_id"),
            patch("utils.github_oauth.GITHUB_CLIENT_SECRET", "test_secret"),
            patch("utils.github_oauth.requests.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "gho_test_token_123",
                "token_type": "bearer",
                "scope": "user:email",
            }
            mock_post.return_value = mock_response

            from utils.github_oauth import exchange_code_for_token

            result = exchange_code_for_token("valid_code")

            assert result == "gho_test_token_123"

    def test_exchange_code_api_error(self):
        """Test returns None on API error response."""
        with (
            patch("utils.github_oauth.GITHUB_CLIENT_ID", "test_client_id"),
            patch("utils.github_oauth.GITHUB_CLIENT_SECRET", "test_secret"),
            patch("utils.github_oauth.requests.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_post.return_value = mock_response

            from utils.github_oauth import exchange_code_for_token

            result = exchange_code_for_token("invalid_code")

            assert result is None

    def test_exchange_code_oauth_error(self):
        """Test returns None when GitHub returns OAuth error."""
        with (
            patch("utils.github_oauth.GITHUB_CLIENT_ID", "test_client_id"),
            patch("utils.github_oauth.GITHUB_CLIENT_SECRET", "test_secret"),
            patch("utils.github_oauth.requests.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "error": "bad_verification_code",
                "error_description": "The code passed is incorrect or expired.",
            }
            mock_post.return_value = mock_response

            from utils.github_oauth import exchange_code_for_token

            result = exchange_code_for_token("expired_code")

            assert result is None

    def test_exchange_code_exception(self):
        """Test returns None on exception."""
        with (
            patch("utils.github_oauth.GITHUB_CLIENT_ID", "test_client_id"),
            patch("utils.github_oauth.GITHUB_CLIENT_SECRET", "test_secret"),
            patch("utils.github_oauth.requests.post") as mock_post,
        ):
            mock_post.side_effect = Exception("Network error")

            from utils.github_oauth import exchange_code_for_token

            result = exchange_code_for_token("test_code")

            assert result is None


class TestGetGitHubUserInfo:
    """Tests for get_github_user_info function."""

    def test_get_user_info_success_with_email(self):
        """Test successful user info retrieval with email in profile."""
        with patch("utils.github_oauth.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": 12345,
                "login": "testuser",
                "name": "Test User",
                "email": "test@example.com",
                "avatar_url": "https://github.com/avatars/testuser",
            }
            mock_get.return_value = mock_response

            from utils.github_oauth import get_github_user_info

            result = get_github_user_info("valid_token")

            assert result is not None
            assert result["id"] == "12345"
            assert result["email"] == "test@example.com"
            assert result["name"] == "Test User"
            assert result["email_verified"] is True

    def test_get_user_info_email_from_separate_endpoint(self):
        """Test getting email from separate emails endpoint."""
        with patch("utils.github_oauth.requests.get") as mock_get:
            # First call returns user without email
            user_response = MagicMock()
            user_response.status_code = 200
            user_response.json.return_value = {
                "id": 12345,
                "login": "testuser",
                "name": "Test User",
                "email": None,
                "avatar_url": "https://github.com/avatars/testuser",
            }

            # Second call returns emails
            emails_response = MagicMock()
            emails_response.status_code = 200
            emails_response.json.return_value = [
                {"email": "private@example.com", "primary": True, "verified": True}
            ]

            mock_get.side_effect = [user_response, emails_response]

            from utils.github_oauth import get_github_user_info

            result = get_github_user_info("valid_token")

            assert result is not None
            assert result["email"] == "private@example.com"

    def test_get_user_info_api_failure(self):
        """Test returns None on API failure."""
        with patch("utils.github_oauth.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Bad credentials"
            mock_get.return_value = mock_response

            from utils.github_oauth import get_github_user_info

            result = get_github_user_info("invalid_token")

            assert result is None

    def test_get_user_info_exception(self):
        """Test returns None on exception."""
        with patch("utils.github_oauth.requests.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            from utils.github_oauth import get_github_user_info

            result = get_github_user_info("token")

            assert result is None


class TestVerifyGitHubAccessToken:
    """Tests for verify_github_access_token function."""

    def test_verify_access_token_delegates_to_get_user_info(self):
        """Test verify_github_access_token calls get_github_user_info."""
        with patch("utils.github_oauth.get_github_user_info") as mock_get_info:
            mock_get_info.return_value = {"id": "12345", "email": "test@example.com"}

            from utils.github_oauth import verify_github_access_token

            result = verify_github_access_token("token")

            assert result is not None
            mock_get_info.assert_called_once_with("token")


class TestAsyncExchangeCodeForToken:
    """Tests for async_exchange_code_for_token function."""

    @pytest.mark.asyncio
    async def test_async_exchange_code_no_credentials(self):
        """Test async version returns None when not configured."""
        with (
            patch("utils.github_oauth.GITHUB_CLIENT_ID", None),
            patch("utils.github_oauth.GITHUB_CLIENT_SECRET", None),
        ):
            from utils.github_oauth import async_exchange_code_for_token

            result = await async_exchange_code_for_token("code")

            assert result is None
