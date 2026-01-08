"""
Tests for utils/google_oauth.py with mocked external calls.

Focus on testable parts without complex import mocking.
"""

from unittest.mock import patch

import pytest


class TestGoogleOAuthConfiguration:
    """Tests for Google OAuth configuration checks."""

    def test_is_google_oauth_configured_function_exists(self):
        """Test is_google_oauth_configured function exists and returns bool."""
        from utils.google_oauth import is_google_oauth_configured

        result = is_google_oauth_configured()

        assert isinstance(result, bool)


class TestVerifyGoogleIdToken:
    """Tests for verify_google_id_token function."""

    def test_verify_id_token_no_client_id(self):
        """Test returns None when client ID not configured."""
        with patch("utils.google_oauth.GOOGLE_CLIENT_ID", None):
            from utils.google_oauth import verify_google_id_token

            result = verify_google_id_token("fake_token")

            assert result is None

    def test_verify_id_token_invalid_issuer(self):
        """Test returns None for invalid token issuer."""
        with patch("utils.google_oauth.GOOGLE_CLIENT_ID", "test_client_id"):
            with patch("utils.google_oauth.id_token.verify_oauth2_token") as mock_verify:
                mock_verify.return_value = {
                    "iss": "invalid.issuer.com",
                    "aud": "test_client_id",
                    "sub": "12345",
                    "email": "test@gmail.com",
                }

                from utils.google_oauth import verify_google_id_token

                result = verify_google_id_token("fake_token")

                assert result is None

    def test_verify_id_token_invalid_audience(self):
        """Test returns None for invalid audience."""
        with patch("utils.google_oauth.GOOGLE_CLIENT_ID", "test_client_id"):
            with patch("utils.google_oauth.id_token.verify_oauth2_token") as mock_verify:
                mock_verify.return_value = {
                    "iss": "accounts.google.com",
                    "aud": "wrong_client_id",
                    "sub": "12345",
                    "email": "test@gmail.com",
                }

                from utils.google_oauth import verify_google_id_token

                result = verify_google_id_token("fake_token")

                assert result is None

    def test_verify_id_token_success(self):
        """Test successful token verification."""
        with patch("utils.google_oauth.GOOGLE_CLIENT_ID", "test_client_id"):
            with patch("utils.google_oauth.id_token.verify_oauth2_token") as mock_verify:
                mock_verify.return_value = {
                    "iss": "accounts.google.com",
                    "aud": "test_client_id",
                    "sub": "12345",
                    "email": "test@gmail.com",
                    "name": "Test User",
                    "picture": "https://example.com/photo.jpg",
                    "email_verified": True,
                }

                from utils.google_oauth import verify_google_id_token

                result = verify_google_id_token("valid_token")

                assert result is not None
                assert result["id"] == "12345"
                assert result["email"] == "test@gmail.com"
                assert result["name"] == "Test User"
                assert result["email_verified"] is True

    def test_verify_id_token_exception(self):
        """Test returns None on exception."""
        with patch("utils.google_oauth.GOOGLE_CLIENT_ID", "test_client_id"):
            with patch("utils.google_oauth.id_token.verify_oauth2_token") as mock_verify:
                mock_verify.side_effect = Exception("Token verification failed")

                from utils.google_oauth import verify_google_id_token

                result = verify_google_id_token("bad_token")

                assert result is None


class TestAsyncVerifyGoogleIdToken:
    """Tests for async_verify_google_id_token function."""

    @pytest.mark.asyncio
    async def test_async_verify_id_token(self):
        """Test async token verification delegates to sync version."""
        with patch("utils.google_oauth.verify_google_id_token") as mock_sync:
            mock_sync.return_value = {"id": "12345", "email": "test@gmail.com", "name": "Test User"}

            from utils.google_oauth import async_verify_google_id_token

            result = await async_verify_google_id_token("token")

            assert result is not None
            assert result["id"] == "12345"
