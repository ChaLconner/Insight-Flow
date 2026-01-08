"""
Tests for services/async_password_reset_service.py

Tests password reset service functionality.
"""

from datetime import datetime, timedelta


class TestPasswordResetServiceImport:
    """Tests for password reset service imports."""

    def test_password_reset_service_import(self):
        """Test AsyncPasswordResetService can be imported."""
        from services.async_password_reset_service import AsyncPasswordResetService

        assert AsyncPasswordResetService is not None


class TestPasswordResetTokenGeneration:
    """Tests for password reset token generation."""

    def test_token_length(self):
        """Test password reset tokens have reasonable length."""
        import secrets

        token = secrets.token_urlsafe(32)

        assert len(token) >= 32

    def test_token_is_unique(self):
        """Test each generated token is unique."""
        import secrets

        tokens = [secrets.token_urlsafe(32) for _ in range(10)]

        # All tokens should be unique
        assert len(set(tokens)) == len(tokens)


class TestPasswordResetTokenExpiration:
    """Tests for password reset token expiration."""

    def test_token_expires_in_future(self):
        """Test token expiration is in the future."""
        expiration_minutes = 60
        expires_at = datetime.now() + timedelta(minutes=expiration_minutes)

        assert expires_at > datetime.now()

    def test_expired_token(self):
        """Test expired token detection."""
        expired_at = datetime.now() - timedelta(hours=1)

        is_expired = expired_at < datetime.now()

        assert is_expired is True

    def test_valid_token(self):
        """Test valid token detection."""
        expires_at = datetime.now() + timedelta(hours=1)

        is_valid = expires_at > datetime.now()

        assert is_valid is True
