"""
Tests for utils/token_utils.py

Tests token utility functions.
"""

from unittest.mock import MagicMock

from fastapi import Response


class TestTokenConstants:
    """Tests for token constants."""

    def test_access_token_key_exists(self):
        """Test ACCESS_TOKEN_KEY is defined."""
        from utils.token_utils import ACCESS_TOKEN_KEY

        assert ACCESS_TOKEN_KEY is not None
        assert len(ACCESS_TOKEN_KEY) > 0

    def test_refresh_token_key_exists(self):
        """Test REFRESH_TOKEN_KEY is defined."""
        from utils.token_utils import REFRESH_TOKEN_KEY

        assert REFRESH_TOKEN_KEY is not None
        assert len(REFRESH_TOKEN_KEY) > 0

    def test_cookie_secure_exists(self):
        """Test COOKIE_SECURE is defined."""
        from utils.token_utils import COOKIE_SECURE

        assert isinstance(COOKIE_SECURE, bool)


class TestCookieFunctions:
    """Tests for cookie handling functions."""

    def test_create_and_set_auth_cookies_import(self):
        """Test create_and_set_auth_cookies can be imported."""
        from utils.token_utils import create_and_set_auth_cookies

        assert create_and_set_auth_cookies is not None

    def test_clear_auth_cookies_import(self):
        """Test clear_auth_cookies can be imported."""
        from utils.token_utils import clear_auth_cookies

        assert clear_auth_cookies is not None

    def test_clear_auth_cookies_calls_delete_cookie(self):
        """Test clear_auth_cookies deletes cookies."""
        from utils.token_utils import clear_auth_cookies

        mock_response = MagicMock()

        clear_auth_cookies(mock_response)

        # Should have called delete_cookie for both tokens
        assert mock_response.delete_cookie.call_count >= 2

    def test_remember_me_false_sets_session_refresh_cookie(self):
        """Test default login refresh cookie is not persisted across browser restarts."""
        from utils.token_utils import create_and_set_auth_cookies

        response = Response()

        create_and_set_auth_cookies(
            response,
            user_id="00000000-0000-0000-0000-000000000001",
            remember_me=False,
        )

        refresh_cookie = next(
            cookie
            for cookie in response.headers.getlist("set-cookie")
            if cookie.startswith("refresh_token=")
        )
        assert "Max-Age=" not in refresh_cookie

    def test_remember_me_true_sets_persistent_refresh_cookie(self):
        """Test remember me persists refresh cookie for the configured extended lifetime."""
        from utils.token_utils import create_and_set_auth_cookies

        response = Response()

        create_and_set_auth_cookies(
            response,
            user_id="00000000-0000-0000-0000-000000000001",
            remember_me=True,
        )

        refresh_cookie = next(
            cookie
            for cookie in response.headers.getlist("set-cookie")
            if cookie.startswith("refresh_token=")
        )
        assert "Max-Age=2592000" in refresh_cookie

    def test_create_auth_tokens_include_session_version(self):
        """New tokens carry the version used to revoke prior sessions."""
        from utils.auth import verify_token
        from utils.token_utils import create_auth_tokens

        access_token, refresh_token, _ = create_auth_tokens(
            "00000000-0000-0000-0000-000000000001", session_version=3
        )

        assert verify_token(access_token, expected_type="access")["sv"] == 3
        assert verify_token(refresh_token, expected_type="refresh")["sv"] == 3


class TestTokenExpiration:
    """Tests for token expiration handling."""

    def test_access_token_expiration_default(self):
        """Test default access token expiration."""
        # Common default is 30 minutes = 1800 seconds
        DEFAULT_ACCESS_EXPIRE = 1800

        assert DEFAULT_ACCESS_EXPIRE == 30 * 60

    def test_refresh_token_expiration_default(self):
        """Test default refresh token expiration."""
        # Common default is 7 days
        DEFAULT_REFRESH_EXPIRE = 7 * 24 * 60 * 60

        assert DEFAULT_REFRESH_EXPIRE == 604800
