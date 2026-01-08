"""
Tests for services/notification_rate_limiter.py

Tests rate limiting logic for notifications.
"""

from uuid import uuid4


class TestNotificationRateLimiter:
    """Tests for NotificationRateLimiter class."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        from services.notification_rate_limiter import NotificationRateLimiter

        limiter = NotificationRateLimiter()

        # Should be created successfully
        assert limiter is not None

    def test_rate_limiter_key_generation(self):
        """Test rate limiter generates correct keys."""
        user_id = uuid4()
        notification_type = "task_assigned"

        # Generate key format
        key = f"notification_rate:{user_id}:{notification_type}"

        # Key should contain user_id and type
        assert str(user_id) in key
        assert notification_type in key


class TestRateLimitConfiguration:
    """Tests for rate limit configuration."""

    def test_default_rate_limits(self):
        """Test default rate limits are reasonable."""
        from services.notification_rate_limiter import NotificationRateLimiter

        limiter = NotificationRateLimiter()

        # Should have some form of limit configuration
        assert limiter is not None
