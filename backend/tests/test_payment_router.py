"""
Comprehensive tests for routers/payment.py endpoints.

Tests focus on payment router endpoints with mocked services.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from dependencies.auth import get_current_user
from main import app
from models.user import User
from routers.payment import get_service
from services.payment_service import get_payment_service

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_payment_service():
    """Mock PaymentService."""
    service = MagicMock()
    service.is_configured = True
    return service


@pytest.fixture
def mock_current_user():
    """Mock User model."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    user.role = "user"
    user.is_active = True
    return user


@pytest.fixture
def client(mock_payment_service, mock_current_user):
    """Test client with mocks."""
    app.dependency_overrides[get_payment_service] = lambda: mock_payment_service
    app.dependency_overrides[get_service] = lambda: mock_payment_service
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
def unauthenticated_client():
    """Test client without authentication."""
    with TestClient(app) as client:
        yield client


# ============================================================================
# Tests for Plans Endpoints
# ============================================================================


class TestPlansEndpoints:
    def test_get_available_plans(self, client):
        """Test getting available subscription plans."""
        response = client.get("/api/v1/payment/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data


# ============================================================================
# Tests for Payment Methods Endpoints
# ============================================================================


class TestPaymentMethodsEndpoints:
    def test_list_payment_methods(self, client, mock_payment_service):
        """Test listing payment methods."""
        mock_payment_service.list_payment_methods = AsyncMock(return_value=[])

        response = client.get("/api/v1/payment/methods")
        assert response.status_code == 200
        data = response.json()
        assert "payment_methods" in data
        assert data["total"] == 0


# ============================================================================
# Tests for Subscription Endpoints
# ============================================================================


class TestSubscriptionEndpoints:
    def test_get_subscription_not_found(self, client, mock_payment_service):
        """Test getting subscription when none exists."""
        mock_payment_service.get_subscription = AsyncMock(return_value=None)

        response = client.get("/api/v1/payment/subscription")
        assert response.status_code == 404


# ============================================================================
# Tests for Payment History Endpoints
# ============================================================================


class TestPaymentHistoryEndpoints:
    def test_list_payment_history(self, client, mock_payment_service):
        """Test listing payment history."""
        mock_payment_service.list_payment_history = AsyncMock(return_value=([], 0))

        response = client.get("/api/v1/payment/history")
        assert response.status_code == 200
        data = response.json()
        assert "payments" in data
        assert data["total"] == 0

    def test_list_payment_history_with_filters(self, client, mock_payment_service):
        """Test listing payment history with filters."""
        mock_payment_service.list_payment_history = AsyncMock(return_value=([], 0))

        response = client.get(
            "/api/v1/payment/history",
            params={
                "status": "succeeded",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "limit": 10,
                "offset": 0,
            },
        )
        assert response.status_code == 200

    def test_list_payment_history_invalid_date(self, client, mock_payment_service):
        """Test payment history with invalid date format."""
        response = client.get("/api/v1/payment/history", params={"start_date": "invalid-date"})
        assert response.status_code == 400

    def test_get_payment_history_stats(self, client, mock_payment_service):
        """Test getting payment history statistics."""
        mock_payment_service.get_payment_history_stats = AsyncMock(
            return_value={
                "total_spent": 100.0,
                "total_payments": 5,
                "successful_payments": 4,
                "failed_payments": 1,
                "pending_payments": 0,
                "refunded_payments": 0,
                "currency": "usd",
            }
        )

        response = client.get("/api/v1/payment/history/stats")
        assert response.status_code == 200


# ============================================================================
# Tests for Authentication
# ============================================================================


class TestPaymentAuthentication:
    def test_plans_public(self, unauthenticated_client):
        """Test plans endpoint is public."""
        response = unauthenticated_client.get("/api/v1/payment/plans")
        # Should be accessible without auth
        assert response.status_code == 200

    def test_methods_requires_auth(self, unauthenticated_client):
        """Test methods endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/payment/methods")
        assert response.status_code == 401

    def test_subscription_requires_auth(self, unauthenticated_client):
        """Test subscription endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/payment/subscription")
        assert response.status_code == 401
