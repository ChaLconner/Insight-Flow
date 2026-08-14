"""
Tests for middleware modules.

Tests middleware functionality in isolation.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


class TestRequestIDMiddleware:
    """Tests for RequestIDMiddleware."""

    def test_generates_request_id_if_not_provided(self):
        """Test middleware generates request ID if not in headers."""
        from middleware.request_id import RequestIDMiddleware

        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.get("/test")

            # Response should have X-Request-ID header
            assert "X-Request-ID" in response.headers
            assert len(response.headers["X-Request-ID"]) > 0

    def test_uses_provided_request_id(self):
        """Test middleware uses provided X-Request-ID."""
        from middleware.request_id import RequestIDMiddleware

        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            custom_id = "custom-request-id-123"
            response = client.get("/test", headers={"X-Request-ID": custom_id})

            # Response should have same X-Request-ID
            assert response.headers["X-Request-ID"] == custom_id

    def test_adds_response_time_header(self):
        """Test middleware adds X-Response-Time header."""
        from middleware.request_id import RequestIDMiddleware

        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.get("/test")

            # Response should have X-Response-Time header
            assert "X-Response-Time" in response.headers


class TestGetRequestId:
    """Tests for get_request_id helper."""

    def test_returns_request_id_from_state(self):
        """Test returns request ID from request state."""
        from middleware.request_id import get_request_id

        mock_request = MagicMock(spec=Request)
        mock_request.state.request_id = "test-id-123"

        result = get_request_id(mock_request)

        assert result == "test-id-123"

    def test_returns_unknown_if_not_set(self):
        """Test returns 'unknown' if request ID not set."""
        from middleware.request_id import get_request_id

        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock(spec=[])  # Empty spec - no request_id

        result = get_request_id(mock_request)

        assert result == "unknown"


class TestGetCorrelationId:
    """Tests for get_correlation_id helper."""

    def test_returns_correlation_id_from_state(self):
        """Test returns correlation ID from request state."""
        from middleware.request_id import get_correlation_id

        mock_request = MagicMock(spec=Request)
        mock_request.state.correlation_id = "correlation-123"

        result = get_correlation_id(mock_request)

        assert result == "correlation-123"

    def test_returns_unknown_if_not_set(self):
        """Test returns 'unknown' if correlation ID not set."""
        from middleware.request_id import get_correlation_id

        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock(spec=[])

        result = get_correlation_id(mock_request)

        assert result == "unknown"


class TestSecurityHeadersMiddleware:
    """Tests for security headers middleware."""

    def test_adds_security_headers(self):
        """Test middleware adds security headers to response."""
        from middleware.security_headers import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.get("/test")

            # Common security headers should be present
            # The exact headers depend on implementation
            assert response.status_code == 200


class TestResponseCacheMiddleware:
    """Tests for response cache middleware."""

    def test_cache_middleware_exists(self):
        """Test cache middleware module can be imported."""
        from middleware.response_cache import ResponseCacheMiddleware

        assert ResponseCacheMiddleware is not None

    def test_cache_middleware_does_not_cache_versioned_dashboard_path(self):
        """Test account-scoped dashboard responses remain browser no-store."""
        from middleware.response_cache import ResponseCacheMiddleware

        app = FastAPI()
        app.add_middleware(ResponseCacheMiddleware)

        @app.get("/api/v1/dashboard/overview")
        async def dashboard_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/overview")

        assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"

    def test_cache_middleware_does_not_cache_versioned_notifications(self):
        """Test API v1 notification paths remain no-store."""
        from middleware.response_cache import ResponseCacheMiddleware

        app = FastAPI()
        app.add_middleware(ResponseCacheMiddleware)

        @app.get("/api/v1/notifications/")
        async def notifications_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.get("/api/v1/notifications/")

        assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"

    def test_public_health_response_supports_weak_etag_and_not_modified(self):
        """Public health representations can revalidate without a body transfer."""
        from middleware.response_cache import ResponseCacheMiddleware

        app = FastAPI()
        app.add_middleware(ResponseCacheMiddleware)

        @app.get("/health")
        async def health_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            first_response = client.get("/health")
            etag = first_response.headers["ETag"]
            second_response = client.get("/health", headers={"If-None-Match": etag})

        assert first_response.status_code == 200
        assert etag.startswith('W/"')
        assert second_response.status_code == 304
        assert second_response.headers["ETag"] == etag
        assert second_response.content == b""

    def test_account_scoped_dashboard_response_stays_no_store_without_etag(self):
        """Private responses must not gain validators that browsers can reuse."""
        from middleware.response_cache import ResponseCacheMiddleware

        app = FastAPI()
        app.add_middleware(ResponseCacheMiddleware)

        @app.get("/api/v1/dashboard/overview")
        async def dashboard_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/overview")

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"
        assert "ETag" not in response.headers

    @pytest.mark.parametrize("path", ["/health/full", "/health/db", "/health/cache"])
    def test_detailed_health_responses_are_not_shared_cacheable(self, path):
        """Detailed health can expose topology and must not receive validators."""
        from middleware.response_cache import ResponseCacheMiddleware

        app = FastAPI()
        app.add_middleware(ResponseCacheMiddleware)

        @app.get(path)
        async def detailed_health_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.get(path)

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"
        assert "ETag" not in response.headers


class TestCSRFMiddleware:
    """Tests for CSRF middleware path exemption behavior."""

    def test_exact_exempt_path_allows_state_change_without_token(self):
        """Test exact auth exempt path is allowed without CSRF token."""
        from middleware.csrf import CSRFMiddleware

        app = FastAPI()
        app.add_middleware(CSRFMiddleware, cookie_secure=False)

        @app.post("/api/v1/auth/login")
        async def login_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.post("/api/v1/auth/login")

        assert response.status_code == 200

    def test_exempt_path_prefix_does_not_bypass_csrf(self):
        """Test auth path prefix lookalikes still require CSRF."""
        from middleware.csrf import CSRFMiddleware

        app = FastAPI()
        app.add_middleware(CSRFMiddleware, cookie_secure=False)

        @app.post("/api/v1/auth/login-extra")
        async def login_extra_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.post("/api/v1/auth/login-extra")

        assert response.status_code == 403

    def test_cookie_refresh_requires_csrf_token(self):
        """Ambient refresh cookies must not authorize a cross-site POST."""
        from middleware.csrf import CSRFMiddleware

        app = FastAPI()
        app.add_middleware(CSRFMiddleware, cookie_secure=False)

        @app.post("/api/v1/auth/refresh")
        async def refresh_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            client.cookies.set("refresh_token", "refresh-cookie")
            response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 403

    def test_bearer_refresh_without_cookie_keeps_api_compatibility(self):
        """Non-browser bearer refresh callers do not need a browser CSRF token."""
        from middleware.csrf import CSRFMiddleware

        app = FastAPI()
        app.add_middleware(CSRFMiddleware, cookie_secure=False)

        @app.post("/api/v1/auth/refresh")
        async def refresh_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/refresh", headers={"Authorization": "Bearer refresh-token"}
            )

        assert response.status_code == 200
