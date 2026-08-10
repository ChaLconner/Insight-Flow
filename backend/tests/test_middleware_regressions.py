from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch

import pytest

from middleware.monitoring import RequestMetrics
from middleware.rate_limit import RateLimitMiddleware
from middleware.redis_rate_limit import RedisRateLimitMiddleware
from rate_limiter import rate_limit_exceeded_handler


def _http_scope(path: str) -> dict:
    return {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
        "scheme": "http",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "should_check"),
    [
        ("/", False),
        ("/health", False),
        ("/health/ready", False),
        ("/metrics", False),
        ("/static/app.js", False),
        ("/api/v1/auth/google", True),
        ("/healthcheck", True),
    ],
)
async def test_redis_rate_limit_exemptions_are_path_segment_aware(path, should_check):
    app = AsyncMock()
    middleware = RedisRateLimitMiddleware(app, redis_client=AsyncMock())
    middleware._check_rate_limit = AsyncMock(return_value=(True, 99))

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message):
        return None

    await middleware(_http_scope(path), receive, send)

    assert middleware._check_rate_limit.await_count == (1 if should_check else 0)
    app.assert_awaited_once()


@pytest.mark.asyncio
async def test_in_memory_rate_limit_uses_same_proxy_aware_ip_for_block_check_and_key():
    app = AsyncMock()
    middleware = RateLimitMiddleware(app)
    middleware._check_ip_block = AsyncMock(return_value=None)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message):
        return None

    with patch("middleware.rate_limit.get_client_ip", return_value="203.0.113.7"):
        await middleware(_http_scope("/api/v1/projects"), receive, send)

    middleware._check_ip_block.assert_awaited_once_with(ANY, "203.0.113.7")
    assert list(middleware.request_history) == ["203.0.113.7:default"]
    app.assert_awaited_once()


def test_prometheus_histogram_export_preserves_cumulative_buckets():
    metrics = RequestMetrics()
    metrics.record("GET", "/example", 200, 0.006)
    metrics.record("GET", "/example", 200, 0.020)

    lines = metrics.get_prometheus_metrics()
    bucket_values = []
    for line in lines:
        if 'http_request_duration_seconds_bucket{method="GET",path="/example"' in line:
            bucket_values.append(int(line.rsplit(" ", 1)[1]))

    assert bucket_values == sorted(bucket_values)
    assert bucket_values[-1] == 2
    assert any(
        line == 'http_request_duration_seconds_count{method="GET",path="/example"} 2'
        for line in lines
    )


def test_rate_limit_error_handler_serializes_limit_header():
    request = SimpleNamespace(
        method="POST",
        url=SimpleNamespace(path="/api/v1/files/upload"),
        state=SimpleNamespace(view_rate_limit=(10, 60)),
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
    )
    exception = SimpleNamespace(detail=(10, 60))

    response = rate_limit_exceeded_handler(request, exception)

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Limit"] == "(10, 60)"
