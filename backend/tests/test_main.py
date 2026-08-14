from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app, create_app


def test_read_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Hello from FastAPI"
    assert "version" in response.json()


def test_minimal_test():
    client = TestClient(app)
    response = client.get("/minimal-test")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Minimal test working"}


def test_openapi_documents_authentication_errors_for_protected_routes():
    schema = app.openapi()

    task_list = schema["paths"]["/api/v1/tasks/"]["get"]
    public_plans = schema["paths"]["/api/v1/payment/plans"]["get"]

    assert "401" in task_list["responses"]
    assert "403" in task_list["responses"]
    assert "401" not in public_plans["responses"]


def test_create_app_disables_docs_when_configured():
    settings = SimpleNamespace(
        app_name="Insight-Flow",
        api_version="1.0.0",
        host="127.0.0.1",
        port=8000,
        environment="development",
        enable_docs=False,
        is_production=False,
    )

    test_app = create_app(settings)

    assert test_app.docs_url is None
    assert test_app.redoc_url is None
    assert test_app.openapi_url is None


def test_create_app_fails_startup_when_db_init_fails_in_production():
    settings = SimpleNamespace(
        app_name="Insight-Flow",
        api_version="1.0.0",
        host="127.0.0.1",
        port=8000,
        environment="production",
        enable_docs=False,
        is_production=True,
    )

    with (
        patch("main.init_database", new=AsyncMock(side_effect=RuntimeError("db down"))),
        patch("main.start_scheduler", return_value=None),
        patch("main.shutdown_scheduler", return_value=None),
    ):
        test_app = create_app(settings)
        with (
            pytest.raises(RuntimeError, match="Database initialization failed in production"),
            TestClient(test_app),
        ):
            pass
