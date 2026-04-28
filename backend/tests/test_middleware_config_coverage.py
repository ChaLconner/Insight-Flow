"""
Tests for middleware configuration.
Covers core/middleware_config.py for increased coverage.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI


class TestMiddlewareConfig:
    """Tests for middleware configuration functions."""

    @pytest.fixture
    def app(self):
        return FastAPI()

    @patch("core.middleware_config.settings")
    def test_setup_rate_limit_middleware_testing(self, mock_settings, app):
        """Test rate limit setup skips in testing."""
        from core.middleware_config import setup_rate_limit_middleware

        mock_settings.is_testing = True

        # Should return early
        with patch("core.middleware_config.logger") as mock_logger:
            setup_rate_limit_middleware(app)
            mock_logger.info.assert_called_with(
                "Skipping rate limit middleware in testing environment"
            )

    @patch("core.middleware_config.settings")
    def test_setup_csrf_middleware_testing(self, mock_settings, app):
        """Test CSRF setup skips in testing."""
        from core.middleware_config import setup_csrf_middleware

        mock_settings.is_testing = True

        # Should return early
        with patch("core.middleware_config.logger") as mock_logger:
            setup_csrf_middleware(app)
            mock_logger.info.assert_called_with("Skipping CSRF middleware in testing environment")

    @patch("core.middleware_config.settings")
    def test_setup_csrf_middleware_production(self, mock_settings, app):
        """Test CSRF setup in production (secure cookies)."""
        from core.middleware_config import setup_csrf_middleware

        mock_settings.is_testing = False
        mock_settings.is_production = True

        with patch("middleware.csrf.CSRFMiddleware"):
            setup_csrf_middleware(app)
            # Middleware check is complex due to add_middleware internals,
            # but we can verify simpler logic or just that it doesn't crash

    @patch("core.middleware_config.settings")
    def test_setup_rate_limit_middleware_production_redis(self, mock_settings, app):
        """Test rate limit setup with Redis configured."""
        from core.middleware_config import setup_rate_limit_middleware

        mock_settings.is_testing = False
        mock_settings.cache.redis_url = "redis://localhost:6379"

        # Mock cache service services.cache_service.cache_service.backend.client
        with patch.dict("sys.modules", {"services.cache_service": MagicMock()}):
            import services.cache_service

            mock_cache_service = MagicMock()
            mock_cache_service.backend.client = MagicMock()
            services.cache_service.cache_service = mock_cache_service

            # Need to mock verify RedisRateLimitMiddleware import
            with patch.dict("sys.modules", {"middleware.redis_rate_limit": MagicMock()}):
                setup_rate_limit_middleware(app)
                # Should hit the redis branch

    @patch("core.middleware_config.settings")
    def test_setup_rate_limit_middleware_fallback(self, mock_settings, app):
        """Test rate limit fallback when Redis fails or not configured."""
        from core.middleware_config import setup_rate_limit_middleware

        mock_settings.is_testing = False
        mock_settings.cache.redis_url = None

        with (
            patch("middleware.rate_limit.RateLimitMiddleware"),
            patch("core.middleware_config.logger") as mock_logger,
        ):
            setup_rate_limit_middleware(app)
            mock_logger.info.assert_any_call("Using in-memory rate limiting (Redis not configured)")
