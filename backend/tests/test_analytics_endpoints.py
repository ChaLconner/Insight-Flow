"""
Tests for routers/analytics.py

Tests for analytics router authentication.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from dependencies.services import get_analytics_service
from main import app
from routers.auth import get_current_active_user
from services.async_analytics_service import AnalyticsRefreshInProgressError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def unauthenticated_client():
    """Test client without authentication."""
    with TestClient(app) as client:
        yield client


# ============================================================================
# Tests for Analytics Authentication
# ============================================================================


class TestAnalyticsAuthentication:
    def test_overview_requires_auth(self, unauthenticated_client):
        """Test analytics overview requires authentication."""
        response = unauthenticated_client.get("/api/v1/analytics/overview")
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.parametrize("period", ["week", "month", "quarter", "year"])
    def test_overview_accepts_frontend_periods(self, unauthenticated_client, monkeypatch, period):
        """Test overview accepts the period values sent by the frontend."""
        user = MagicMock(id=uuid.uuid4())
        analytics_service = MagicMock()
        analytics_service.get_analytics_overview = AsyncMock(return_value={"overview": {}})

        monkeypatch.setitem(app.dependency_overrides, get_current_active_user, lambda: user)
        monkeypatch.setitem(
            app.dependency_overrides, get_analytics_service, lambda: analytics_service
        )

        response = unauthenticated_client.get(f"/api/v1/analytics/overview?period={period}")

        assert response.status_code == 200, response.text
        analytics_service.get_analytics_overview.assert_awaited_once_with(user.id, period=period)

    def test_overview_returns_retryable_response_when_refresh_is_busy(
        self, unauthenticated_client, monkeypatch
    ):
        user = MagicMock(id=uuid.uuid4())
        analytics_service = MagicMock()
        analytics_service.get_analytics_overview = AsyncMock(
            side_effect=AnalyticsRefreshInProgressError()
        )

        monkeypatch.setitem(app.dependency_overrides, get_current_active_user, lambda: user)
        monkeypatch.setitem(
            app.dependency_overrides, get_analytics_service, lambda: analytics_service
        )

        response = unauthenticated_client.get("/api/v1/analytics/overview")

        assert response.status_code == 503
        assert response.headers["Retry-After"] == "2"
