from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from main import app
from services.payment_service import PaymentService


@pytest.fixture
def mock_payment_service():
    mock = MagicMock(spec=PaymentService)
    # mock.is_configured is a property in the spec, so we treat it as an attribute here
    # which is standard for MagicMock instances unless PropertyMock is used on the class.
    # To be safe, we just set the attribute.
    mock.is_configured = True
    return mock


@pytest.fixture
def override_payment_service(mock_payment_service):
    from routers.payment import get_service

    app.dependency_overrides[get_service] = lambda: mock_payment_service
    yield mock_payment_service
    # Keep other overrides (from client fixture) intact, only remove this one
    del app.dependency_overrides[get_service]


def test_set_default_payment_method_not_found(client, override_payment_service):
    # Mock return None (not found)
    override_payment_service.set_default_payment_method = AsyncMock(return_value=None)

    pm_id = uuid4()
    response = client.put(f"/api/v1/payment/methods/{pm_id}/default")
    assert response.status_code == 404
    # Custom exception handler returns "message"
    assert "Payment method not found" in response.json().get("message", "")


def test_set_default_payment_method_not_configured(client, override_payment_service):
    # Depending on how spec=PaymentService handles properties, we might need to rely
    # on just setting the attribute on the instance.
    override_payment_service.is_configured = False

    pm_id = uuid4()
    response = client.put(f"/api/v1/payment/methods/{pm_id}/default")
    assert response.status_code == 503
    assert "not configured" in response.json().get("message", "")


def test_delete_payment_method_not_found(client, override_payment_service):
    override_payment_service.delete_payment_method = AsyncMock(return_value=False)

    pm_id = uuid4()
    response = client.delete(f"/api/v1/payment/methods/{pm_id}")
    assert response.status_code == 404
    assert "Payment method not found" in response.json().get("message", "")


def test_cancel_subscription_not_found(client, override_payment_service):
    override_payment_service.cancel_subscription = AsyncMock(return_value=None)

    response = client.delete("/api/v1/payment/subscription")
    assert response.status_code == 404
    assert "No subscription found" in response.json().get("message", "")


def test_resume_subscription_not_found(client, override_payment_service):
    override_payment_service.resume_subscription = AsyncMock(return_value=None)

    response = client.post("/api/v1/payment/subscription/resume")
    assert response.status_code == 404
    assert "No subscription found" in response.json().get("message", "")


def test_create_subscription_service_unavailable(client, override_payment_service):
    override_payment_service.is_configured = False

    response = client.post("/api/v1/payment/subscription", json={"plan": "pro"})
    assert response.status_code == 503
    assert "not configured" in response.json().get("message", "")
