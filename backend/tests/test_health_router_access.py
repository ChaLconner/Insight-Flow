from types import SimpleNamespace

from fastapi.testclient import TestClient

from main import app


def _make_settings(**overrides):
    base = {
        "environment": "development",
        "api_version": "1.0.0",
        "enable_metrics": True,
        "enable_detailed_health": False,
        "is_development": False,
        "is_testing": False,
        "is_production": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_metrics_returns_404_when_disabled(monkeypatch):
    from routers import health

    monkeypatch.setattr(health, "get_settings", lambda: _make_settings(enable_metrics=False))

    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 404


def test_metrics_returns_404_by_default_in_production(monkeypatch):
    from routers import health

    monkeypatch.delenv("ENABLE_METRICS", raising=False)
    monkeypatch.setattr(
        health, "get_settings", lambda: _make_settings(environment="production", is_production=True)
    )

    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 404


def test_detailed_health_returns_404_when_not_enabled(monkeypatch):
    from routers import health

    monkeypatch.setattr(health, "get_settings", lambda: _make_settings())

    with TestClient(app) as client:
        response = client.get("/health/full")

    assert response.status_code == 404
