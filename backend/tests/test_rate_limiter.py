"""
Comprehensive tests for rate_limiter.py

Tests follow best practices:
- Unit tests for individual functions
- Integration tests with mocked dependencies
- Edge case testing
- Clear separation of concerns
"""

from unittest.mock import MagicMock, patch

from fastapi import Request


class TestGetUserIdentifier:
    """Tests for get_user_identifier function."""

    def test_returns_user_id_when_authenticated(self):
        """Test returns user ID when user is in request state."""
        from rate_limiter import get_user_identifier

        # Arrange
        mock_request = MagicMock(spec=Request)
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_request.state.user = mock_user

        # Act
        result = get_user_identifier(mock_request)

        # Assert
        assert result == "user:user-123"

    def test_returns_ip_when_not_authenticated(self):
        """Test returns IP address when user is not authenticated."""
        from rate_limiter import get_user_identifier

        # Arrange
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        del mock_request.state.user  # No user attribute
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.1"

        # Act
        with patch("rate_limiter.get_remote_address", return_value="192.168.1.1"):
            result = get_user_identifier(mock_request)

        # Assert
        assert result == "192.168.1.1"

    def test_returns_ip_when_user_is_none(self):
        """Test returns IP when user is None."""
        from rate_limiter import get_user_identifier

        # Arrange
        mock_request = MagicMock(spec=Request)
        mock_request.state.user = None
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.1"

        # Act
        with patch("rate_limiter.get_remote_address", return_value="10.0.0.1"):
            result = get_user_identifier(mock_request)

        # Assert
        assert result == "10.0.0.1"


class TestRateLimits:
    """Tests for RateLimits configuration class."""

    def test_payment_limits_are_restrictive(self):
        """Test payment-related limits are appropriately restrictive."""
        from rate_limiter import RateLimits

        # Assert - payment limits should be low (security concern)
        assert "5/minute" in RateLimits.PAYMENT_SETUP_INTENT
        assert "10/minute" in RateLimits.PAYMENT_ADD_METHOD
        assert "5/minute" in RateLimits.PAYMENT_SUBSCRIPTION

    def test_auth_limits_prevent_brute_force(self):
        """Test auth limits are set to prevent brute force attacks."""
        from rate_limiter import RateLimits

        # Assert - auth limits prevent rapid attempts
        assert "10/minute" in RateLimits.AUTH_LOGIN
        assert "5/minute" in RateLimits.AUTH_REGISTER
        assert "3/minute" in RateLimits.AUTH_CREDENTIAL_RESET

    def test_api_read_limits_are_higher(self):
        """Test read operations have higher limits than writes."""
        from rate_limiter import RateLimits

        # Parse limits to compare
        def parse_limit(limit_str):
            return int(limit_str.split("/")[0])

        read_limit = parse_limit(RateLimits.API_READ)
        write_limit = parse_limit(RateLimits.API_WRITE)

        # Assert - reads should be more lenient
        assert read_limit > write_limit

    def test_webhook_limit_is_high(self):
        """Test webhook limit is high for Stripe events."""
        from rate_limiter import RateLimits

        def parse_limit(limit_str):
            return int(limit_str.split("/")[0])

        webhook_limit = parse_limit(RateLimits.WEBHOOK)

        # Assert - webhooks need high limit
        assert webhook_limit >= 300


class TestRateLimitExceededHandler:
    """Tests for rate_limit_exceeded_handler function."""

    def test_returns_429_status_code(self):
        """Test handler returns 429 Too Many Requests."""
        from slowapi.errors import RateLimitExceeded

        from rate_limiter import rate_limit_exceeded_handler

        # Arrange
        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/test"
        mock_request.state = MagicMock()
        del mock_request.state.user  # No user
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_exc = MagicMock(spec=RateLimitExceeded)
        mock_exc.detail = "60"

        # Act
        with patch("rate_limiter.get_remote_address", return_value="127.0.0.1"):
            response = rate_limit_exceeded_handler(mock_request, mock_exc)

        # Assert
        assert response.status_code == 429

    def test_includes_retry_after_header(self):
        """Test handler includes Retry-After header."""
        from slowapi.errors import RateLimitExceeded

        from rate_limiter import rate_limit_exceeded_handler

        # Arrange
        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/v1/login"
        mock_request.state = MagicMock()
        mock_request.state.user = None
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        # Remove view_rate_limit attribute
        if hasattr(mock_request.state, "view_rate_limit"):
            del mock_request.state.view_rate_limit

        mock_exc = MagicMock(spec=RateLimitExceeded)
        mock_exc.detail = "30"

        # Act
        with patch("rate_limiter.get_remote_address", return_value="127.0.0.1"):
            response = rate_limit_exceeded_handler(mock_request, mock_exc)

        # Assert
        assert "Retry-After" in response.headers


class TestAuthRateLimiter:
    """Tests for AuthRateLimiter class."""

    def test_initialization_with_defaults(self):
        """Test AuthRateLimiter initializes with default values."""
        from rate_limiter import AuthRateLimiter

        # Act
        limiter = AuthRateLimiter()

        # Assert - check default values
        assert limiter.requests == 5
        assert limiter.window == 60

    def test_initialization_with_custom_values(self):
        """Test AuthRateLimiter accepts custom values."""
        from rate_limiter import AuthRateLimiter

        # Act
        limiter = AuthRateLimiter(requests=10, window=120)

        # Assert
        assert limiter.requests == 10
        assert limiter.window == 120

    def test_auth_rate_limiter_has_cache_service(self):
        """Test AuthRateLimiter has cache service."""
        from rate_limiter import AuthRateLimiter

        # Act
        limiter = AuthRateLimiter()

        # Assert
        assert limiter.cache_service is not None

    def test_auth_rate_limiter_uses_isolated_key_namespace(self):
        """Auth counters must not share keys with the global Redis sorted sets."""
        from rate_limiter import AuthRateLimiter

        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/auth/login"

        with patch("rate_limiter.get_client_ip", return_value="198.51.100.1"):
            assert AuthRateLimiter()._get_key(request) == (
                "auth_rate_limit:198.51.100.1:/api/v1/auth/login"
            )


class TestLimiterInstance:
    """Tests for the global limiter instance."""

    def test_limiter_is_created(self):
        """Test limiter instance exists."""
        from rate_limiter import limiter

        # Assert
        assert limiter is not None

    def test_auth_rate_limiter_instance_exists(self):
        """Test auth_rate_limiter instance is pre-configured."""
        from rate_limiter import AuthRateLimiter, auth_rate_limiter

        # Assert
        assert isinstance(auth_rate_limiter, AuthRateLimiter)
        assert auth_rate_limiter.requests == 5
        assert auth_rate_limiter.window == 60
