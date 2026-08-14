"""Regression tests for normalized production security-header policy."""

from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_hsts_uses_normalized_production_settings():
    """HSTS must remain enabled when ENVIRONMENT casing differs."""
    from middleware.security_headers import SecurityHeadersMiddleware

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/health")
    async def health():
        return {"ok": True}

    settings = SimpleNamespace(
        is_production=True,
        security_report_uri=None,
    )
    with patch("middleware.security_headers.get_settings", return_value=settings):
        response = TestClient(app).get("/health")

    assert response.headers["Strict-Transport-Security"] == (
        "max-age=31536000; includeSubDomains; preload"
    )
