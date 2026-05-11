from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from dependencies.auth import get_current_user
from main import app
from models.user import User
from routers.payment import get_service, is_ip_in_cidr, is_stripe_ip
from services.payment_service import get_payment_service as get_payment_service_dep

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
    return user


@pytest.fixture
def client(mock_payment_service, mock_current_user):
    """Test client with mocks."""
    app.dependency_overrides[get_payment_service_dep] = lambda: mock_payment_service
    app.dependency_overrides[get_service] = lambda: mock_payment_service
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    # Mock database dependency for downgrade check
    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock()

    from database import get_async_db

    app.dependency_overrides[get_async_db] = lambda: mock_db

    with TestClient(app) as client:
        # Attach db to client for test access
        client.mock_db = mock_db
        yield client

    app.dependency_overrides = {}


# ============================================================================
# Tests
# ============================================================================


def test_ip_helpers():
    """Unit test for IP checking helpers."""
    # CIDR check
    assert is_ip_in_cidr("192.168.1.5", "192.168.1.0/24") is True
    assert is_ip_in_cidr("192.168.2.1", "192.168.1.0/24") is False
    assert is_ip_in_cidr("invalid", "192.168.1.0/24") is False

    # Stripe IP check
    assert is_stripe_ip("3.18.12.63") is True  # Direct match
    assert is_stripe_ip("54.88.130.50") is True  # CIDR match (54.88.130.0/24)
    assert is_stripe_ip("1.2.3.4") is False


class TestDowngradeCheck:
    def test_check_downgrade_invalid_plan(self, client):
        response = client.get("/api/v1/payment/plans/check-downgrade/INVALID_PLAN")
        assert response.status_code == 400
        # Exception handler returns "message"
        assert "Invalid plan" in response.json()["message"]

    def test_check_downgrade_success(self, client):
        # Mock DB scalars (project count, team count)
        client.mock_db.scalar.side_effect = [2, 3]  # 2 projects, 3 members

        response = client.get("/api/v1/payment/plans/check-downgrade/starter")

        assert response.status_code == 200
        data = response.json()
        assert data["can_downgrade"] is True
        assert data["current_usage"]["projects"] == 2
        assert len(data["warnings"]) == 0

    def test_check_downgrade_exceeded(self, client):
        # Mock DB scalars (project count, team count)
        # Starter limit is 3 projects, 5 members (usually, referencing schemas/payment.py PLAN_DETAILS)
        # Let's assume Free is target: 1 project, 1 member

        client.mock_db.scalar.side_effect = [5, 5]  # 5 projects, 5 members

        response = client.get("/api/v1/payment/plans/check-downgrade/free")

        assert response.status_code == 200
        data = response.json()
        assert data["can_downgrade"] is False
        assert len(data["warnings"]) >= 1


class TestServiceNotConfigured:
    def test_create_setup_intent_not_configured(self, client, mock_payment_service):
        mock_payment_service.is_configured = False
        response = client.post("/api/v1/payment/setup-intent")
        assert response.status_code == 503

    def test_add_payment_method_not_configured(self, client, mock_payment_service):
        mock_payment_service.is_configured = False
        # Valid payload but service not configured
        response = client.post(
            "/api/v1/payment/methods",
            json={"payment_method_id": "pm_123", "set_as_default": True},
        )
        assert response.status_code == 503

    def test_create_subscription_not_configured(self, client, mock_payment_service):
        mock_payment_service.is_configured = False
        response = client.post("/api/v1/payment/subscription", json={"plan": "pro"})
        assert response.status_code == 503


class TestExceptions:
    def test_create_setup_intent_error(self, client, mock_payment_service):
        mock_payment_service.create_setup_intent = AsyncMock(side_effect=Exception("Stripe Error"))

        with patch("routers.payment.log_and_get_safe_error") as mock_logger:
            mock_logger.return_value = "Safe Error Message"

            response = client.post("/api/v1/payment/setup-intent")

            assert response.status_code == 500
            # Since explicit HTTPException(500) is raised by router, it goes to http_exception_handler
            # which preserves the detail message
            assert response.json()["message"] == "Safe Error Message"

    def test_create_subscription_validation_error(self, client, mock_payment_service):
        mock_payment_service.get_or_create_stripe_customer = AsyncMock(return_value="cus_1")
        # Raising exact error message that is in SAFE list (lowercase 'plan')
        mock_payment_service.create_or_update_subscription = AsyncMock(
            side_effect=ValueError("Invalid plan")
        )

        response = client.post("/api/v1/payment/subscription", json={"plan": "pro"})

        response = client.post("/api/v1/payment/subscription", json={"plan": "pro"})

        assert response.status_code == 400
        # Value error handler uses "message"
        # The mock raises ValueError("Invalid plan") -> which is in safe list
        # So it should return "Invalid plan"
        assert response.json()["message"] == "Invalid plan"


class TestWebhookSecurity:
    def test_webhook_no_secret(self, client):
        with patch("config.get_settings") as mock_settings:
            mock_settings.return_value.is_production = False
            mock_settings.return_value.stripe.webhook_secret = None

            response = client.post("/api/v1/payment/webhook")
            assert response.status_code == 503

    def test_webhook_ip_check_production_bypass(self, client):
        with patch("config.get_settings") as mock_settings:
            mock_settings.return_value.is_production = True
            mock_settings.return_value.stripe.webhook_secret = "whsec_test"

            # Mock get_client_ip
            with patch("routers.payment.get_client_ip", return_value="1.2.3.4"):
                # Should fail IP check
                response = client.post("/api/v1/payment/webhook")
                assert response.status_code == 403

    def test_webhook_ip_check_production_pass(self, client):
        with patch("config.get_settings") as mock_settings:
            mock_settings.return_value.is_production = True
            mock_settings.return_value.stripe.webhook_secret = "whsec_test"

            with patch("routers.payment.get_client_ip", return_value="3.18.12.63"):
                # Pass IP check, fail signature (expected 400)
                response = client.post(
                    "/api/v1/payment/webhook", headers={"stripe-signature": "sig"}
                )
                assert response.status_code == 400
                # Real stripe SDK raises SignatureVerificationError on garbage sig
                assert response.json()["message"] == "Invalid signature"
