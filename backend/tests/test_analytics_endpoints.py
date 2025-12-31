"""
Tests for routers/analytics.py

Tests for analytics router authentication.
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from main import app


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
