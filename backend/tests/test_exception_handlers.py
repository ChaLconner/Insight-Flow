"""
Tests for exception handlers.
Covers exception_handlers.py for increased coverage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_handlers():
    """Create a FastAPI app with exception handlers registered."""
    from exception_handlers import add_exception_handlers
    from utils.exceptions import AppError

    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/test-http-404")
    async def test_404():
        raise HTTPException(status_code=404, detail="Not found")

    @app.get("/test-http-403")
    async def test_403():
        raise HTTPException(status_code=403, detail="Forbidden access")

    @app.get("/test-http-500")
    async def test_500():
        raise HTTPException(status_code=500, detail="Internal error")

    @app.get("/test-validation-error")
    async def test_validation(required_param: int):
        return {"param": required_param}

    @app.get("/test-app-error")
    async def test_app_error():
        raise AppError(
            message="Custom app error",
            status_code=400,
            code="CUSTOM_ERROR",
            details={"field": "value"},
        )

    @app.get("/test-value-error-safe")
    async def test_value_error_safe():
        raise ValueError("User not found")

    @app.get("/test-value-error-unsafe")
    async def test_value_error_unsafe():
        raise ValueError("Internal system error with sensitive data")

    @app.get("/test-generic-exception")
    async def test_generic():
        raise RuntimeError("Unexpected error")

    return app


@pytest.fixture
def client(app_with_handlers):
    """Create test client for app with handlers."""
    return TestClient(app_with_handlers, raise_server_exceptions=False)


class TestHTTPExceptionHandler:
    """Tests for HTTP exception handler."""

    def test_404_error(self, client):
        """Test 404 error returns standard format."""
        response = client.get("/test-http-404")

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Not found"
        assert data["code"] == 404

    def test_403_error_logs_security_event(self, client):
        """Test 403 error logs security event."""
        with patch("exception_handlers.AsyncSessionLocal") as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            response = client.get("/test-http-403")

            assert response.status_code == 403
            data = response.json()
            assert data["success"] is False
            assert data["message"] == "Forbidden access"

    def test_500_error(self, client):
        """Test 500 error returns standard format."""
        response = client.get("/test-http-500")

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Internal error"


class TestValidationExceptionHandler:
    """Tests for validation exception handler."""

    def test_missing_required_param(self, client):
        """Test missing required parameter returns 422."""
        response = client.get("/test-validation-error")

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "errors" in data

    def test_invalid_param_type(self, client):
        """Test invalid parameter type returns 422."""
        response = client.get("/test-validation-error?required_param=not_an_int")

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "errors" in data
        # Errors should not contain sensitive 'ctx' or 'url' fields
        for error in data["errors"]:
            assert "ctx" not in error
            assert "url" not in error


class TestAppErrorHandler:
    """Tests for AppError handler."""

    def test_app_error_returns_custom_response(self, client):
        """Test AppError returns custom response format."""
        response = client.get("/test-app-error")

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Custom app error"
        assert data["code"] == "CUSTOM_ERROR"
        assert data["details"] == {"field": "value"}


class TestValueErrorHandler:
    """Tests for ValueError handler."""

    def test_safe_value_error_exposed(self, client):
        """Test safe ValueError message is exposed."""
        response = client.get("/test-value-error-safe")

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "User not found"
        assert data["code"] == "BAD_REQUEST"

    def test_unsafe_value_error_hidden(self, client):
        """Test unsafe ValueError message is hidden."""
        response = client.get("/test-value-error-unsafe")

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        # Should return generic message, not the actual error
        assert data["message"] == "Invalid request"
        assert data["code"] == "BAD_REQUEST"


class TestGlobalExceptionHandler:
    """Tests for global exception handler."""

    def test_generic_exception_hidden_in_production(self, client):
        """Test generic exception is hidden in production."""
        with patch("exception_handlers.get_settings") as mock_settings:
            mock_settings.return_value.environment = "production"

            response = client.get("/test-generic-exception")

            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert "error_id" in data
            assert data["message"] == "An unexpected error occurred. Please try again later."
            # Should NOT contain detail in production
            assert "detail" not in data
            assert "type" not in data

    def test_generic_exception_exposed_in_development(self, client):
        """Test generic exception is exposed in development."""
        with patch("exception_handlers.get_settings") as mock_settings:
            mock_settings.return_value.environment = "development"

            response = client.get("/test-generic-exception")

            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert "error_id" in data
            # Should contain detail in development
            assert "detail" in data
            assert "type" in data
            assert data["type"] == "RuntimeError"


class TestIntegrityErrorHandler:
    """Tests for IntegrityError handler."""

    @pytest.fixture
    def app_with_integrity_error(self):
        """Create app that raises IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        from exception_handlers import add_exception_handlers

        app = FastAPI()
        add_exception_handlers(app)

        @app.get("/test-unique-constraint")
        async def test_unique():
            error = MagicMock()
            error.orig = Exception("unique constraint violation")
            raise IntegrityError(
                statement="INSERT INTO users",
                params={},
                orig=error.orig,
            )

        @app.get("/test-foreign-key")
        async def test_fk():
            error = MagicMock()
            error.orig = Exception("foreign key constraint violation")
            raise IntegrityError(
                statement="INSERT INTO tasks",
                params={},
                orig=error.orig,
            )

        @app.get("/test-not-null")
        async def test_not_null():
            error = MagicMock()
            error.orig = Exception("not null constraint violation")
            raise IntegrityError(
                statement="INSERT INTO projects",
                params={},
                orig=error.orig,
            )

        @app.get("/test-generic-integrity")
        async def test_generic_integrity():
            raise IntegrityError(
                statement="UPDATE users",
                params={},
                orig=None,
            )

        return app

    def test_unique_constraint_error(self, app_with_integrity_error):
        """Test unique constraint error returns appropriate message."""
        client = TestClient(app_with_integrity_error, raise_server_exceptions=False)

        response = client.get("/test-unique-constraint")

        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "This record already exists"
        assert data["code"] == "CONFLICT"

    def test_foreign_key_error(self, app_with_integrity_error):
        """Test foreign key error returns appropriate message."""
        client = TestClient(app_with_integrity_error, raise_server_exceptions=False)

        response = client.get("/test-foreign-key")

        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Referenced record not found"

    def test_not_null_error(self, app_with_integrity_error):
        """Test not null error returns appropriate message."""
        client = TestClient(app_with_integrity_error, raise_server_exceptions=False)

        response = client.get("/test-not-null")

        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Required field is missing"

    def test_generic_integrity_error(self, app_with_integrity_error):
        """Test generic integrity error returns default message."""
        client = TestClient(app_with_integrity_error, raise_server_exceptions=False)

        response = client.get("/test-generic-integrity")

        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "A conflict occurred while processing your request"


class TestAdditionalValueErrors:
    """Test additional safe ValueError messages."""

    @pytest.fixture
    def app_with_value_errors(self):
        """Create app with various ValueError scenarios."""
        from exception_handlers import add_exception_handlers

        app = FastAPI()
        add_exception_handlers(app)

        @app.get("/test-email-registered")
        async def test_email():
            raise ValueError("Email already registered")

        @app.get("/test-username-taken")
        async def test_username():
            raise ValueError("Username already taken")

        @app.get("/test-incorrect-password")
        async def test_password():
            raise ValueError("Incorrect current password")

        @app.get("/test-invalid-plan")
        async def test_plan():
            raise ValueError("Invalid plan")

        @app.get("/test-plan-not-found")
        async def test_plan_not_found():
            raise ValueError("Plan not found")

        @app.get("/test-failed-invite")
        async def test_invite():
            raise ValueError("Failed to invite user")

        return app

    def test_email_already_registered(self, app_with_value_errors):
        """Test email already registered message is exposed."""
        client = TestClient(app_with_value_errors, raise_server_exceptions=False)

        response = client.get("/test-email-registered")

        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "Email already registered"

    def test_username_already_taken(self, app_with_value_errors):
        """Test username already taken message is exposed."""
        client = TestClient(app_with_value_errors, raise_server_exceptions=False)

        response = client.get("/test-username-taken")

        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "Username already taken"

    def test_incorrect_password(self, app_with_value_errors):
        """Test incorrect password message is exposed."""
        client = TestClient(app_with_value_errors, raise_server_exceptions=False)

        response = client.get("/test-incorrect-password")

        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "Incorrect current password"

    def test_invalid_plan(self, app_with_value_errors):
        """Test invalid plan message is exposed."""
        client = TestClient(app_with_value_errors, raise_server_exceptions=False)

        response = client.get("/test-invalid-plan")

        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "Invalid plan"

    def test_plan_not_found(self, app_with_value_errors):
        """Test plan not found message is exposed."""
        client = TestClient(app_with_value_errors, raise_server_exceptions=False)

        response = client.get("/test-plan-not-found")

        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "Plan not found"

    def test_failed_invite(self, app_with_value_errors):
        """Test failed invite message is exposed."""
        client = TestClient(app_with_value_errors, raise_server_exceptions=False)

        response = client.get("/test-failed-invite")

        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "Failed to invite user"
