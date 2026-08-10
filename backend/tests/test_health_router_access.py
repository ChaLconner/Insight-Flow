from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
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


@pytest.mark.asyncio
async def test_readiness_reuses_short_lived_probe(monkeypatch):
    from routers import health

    settings = _make_settings(
        cache=SimpleNamespace(redis_url=None), health_check_cache_ttl_seconds=60
    )
    probe = AsyncMock(return_value={"healthy": True})
    monkeypatch.setattr(health, "get_settings", lambda: settings)
    monkeypatch.setattr(health, "_probe_database", probe)
    health._readiness_cache = None

    first = await health.readiness_check()
    second = await health.readiness_check()

    assert first.status_code == 200
    assert second.status_code == 200
    probe.assert_awaited_once()


@pytest.mark.asyncio
async def test_readiness_ignores_redis_when_cache_is_disabled(monkeypatch):
    from routers import health
    from services.cache_service import cache_service

    settings = _make_settings(
        cache=SimpleNamespace(enabled=False, redis_url="redis://configured-but-disabled"),
        health_check_cache_ttl_seconds=0,
    )
    monkeypatch.setattr(health, "get_settings", lambda: settings)
    monkeypatch.setattr(health, "_probe_database", AsyncMock(return_value={"healthy": True}))
    monkeypatch.setattr(cache_service, "ensure_connected", AsyncMock(return_value=False))
    health._readiness_cache = None

    response = await health.readiness_check()

    assert response.status_code == 200
