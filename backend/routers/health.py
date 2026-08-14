"""
Health check router for monitoring and observability.
Provides endpoints for Kubernetes liveness/readiness probes and general health monitoring.
"""

import asyncio
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse, PlainTextResponse

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger("health_router")

router = APIRouter(tags=["health"])

_db_probe_lock = asyncio.Lock()
_db_probe_cache: tuple[float, dict[str, Any]] | None = None
_readiness_lock = asyncio.Lock()
_readiness_cache: tuple[float, dict[str, Any]] | None = None


def _settings():
    return get_settings()


def _health_timeout(settings: Any) -> float:
    """Return a bounded timeout for dependency probes."""
    return max(0.1, float(getattr(settings, "health_check_timeout_seconds", 2.0)))


def _require_metrics_enabled() -> Any:
    settings = _settings()
    metrics_enabled = getattr(settings, "metrics_enabled", None)
    if metrics_enabled is None:
        metrics_enabled = settings.enable_metrics
        if settings.is_production:
            metrics_enabled = False
    if not metrics_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics endpoint is disabled",
        )
    return settings


def _require_detailed_health_enabled() -> Any:
    settings = _settings()
    if settings.enable_detailed_health or settings.is_development or settings.is_testing:
        return settings
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Detailed health endpoint is disabled",
    )


@router.get("/")
def read_root():
    """Root endpoint - basic API info."""
    settings = _settings()
    return {"message": "Hello from FastAPI", "version": settings.api_version}


@router.get("/minimal-test")
def minimal_test():
    """Minimal test endpoint to check if FastAPI is responsive."""
    return {"status": "success", "message": "Minimal test working"}


@router.get("/health")
async def health_check():
    """
    Process liveness check. This endpoint intentionally avoids dependencies.
    """
    settings = _settings()
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": settings.api_version,
    }


@router.get("/health/ready")
async def readiness_check():
    """Return 200 only when required runtime dependencies are reachable."""
    global _readiness_cache

    settings = _settings()
    from services.cache_service import cache_service

    try:
        now = time.monotonic()
        ttl = float(getattr(settings, "health_check_cache_ttl_seconds", 1.0))
        if _readiness_cache and ttl > 0 and now - _readiness_cache[0] < ttl:
            payload = _readiness_cache[1]
            return JSONResponse(status_code=payload["status_code"], content=payload["body"])

        async with _readiness_lock:
            now = time.monotonic()
            if _readiness_cache and ttl > 0 and now - _readiness_cache[0] < ttl:
                payload = _readiness_cache[1]
                return JSONResponse(status_code=payload["status_code"], content=payload["body"])

            timeout = _health_timeout(settings)
            probe = await asyncio.wait_for(_probe_database(settings), timeout=timeout)
            cache_enabled = getattr(settings.cache, "enabled", True)
            redis_unavailable = (
                cache_enabled
                and settings.cache.redis_url
                and not await asyncio.wait_for(cache_service.ensure_connected(), timeout=timeout)
            )
            if not probe["healthy"] or redis_unavailable:
                payload = {
                    "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
                    "body": {"status": "not_ready"},
                }
            else:
                payload = {"status_code": status.HTTP_200_OK, "body": {"status": "ready"}}

            if ttl > 0:
                _readiness_cache = (time.monotonic(), payload)
            return JSONResponse(status_code=payload["status_code"], content=payload["body"])
    except Exception as e:
        logger.exception(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready"},
        )


@router.get("/health/db")
async def db_health_check():
    """
    Database health check with connection pool statistics.
    Useful for monitoring and debugging connection issues.
    """
    settings = _require_detailed_health_enabled()
    probe = await _probe_database(settings)
    if not probe["healthy"]:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected", "error": probe["error"]},
        )

    return {
        "status": "healthy",
        "database": "connected",
        "async_pool": {
            **probe["pool"],
            "pool_size": settings.database.pool_size,
            "max_overflow": settings.database.max_overflow,
        },
        "host": settings.database.url.split("@")[-1].split("/")[0]
        if "@" in settings.database.url
        else "unknown",
        "probe_cached": probe["cached"],
    }


@router.get("/health/cache")
async def cache_health_check():
    """
    Cache health check with statistics.
    """
    _require_detailed_health_enabled()
    from services.cache_service import cache_service

    try:
        stats = await cache_service.get_stats()
        if stats.get("health", {}).get("status") == "unhealthy":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unhealthy", "cache": stats},
            )
        return {"status": "healthy", "cache": stats}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)},
        )


@router.get("/health/full")
async def full_health_check():
    """
    Comprehensive health check for all system components.
    Useful for Kubernetes liveness/readiness probes.
    """
    settings = _require_detailed_health_enabled()
    import psutil

    from services.cache_service import cache_service

    health_status: dict[str, Any] = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.environment,
        "version": settings.api_version,
        "components": {},
    }

    # Database and cache probes are independent. Run them concurrently and
    # bound each one so a degraded dependency cannot block the entire health
    # response or consume an application worker indefinitely.
    timeout = _health_timeout(settings)
    results = await asyncio.gather(
        asyncio.wait_for(_probe_database(settings), timeout=timeout),
        asyncio.wait_for(cache_service.get_stats(), timeout=timeout),
        return_exceptions=True,
    )
    raw_probe: Any = results[0]
    raw_cache: Any = results[1]

    if isinstance(raw_probe, BaseException):
        probe: dict[str, Any] = {
            "healthy": False,
            "error": "Database health probe timed out"
            if isinstance(raw_probe, TimeoutError)
            else str(raw_probe),
        }
    elif isinstance(raw_probe, dict):
        probe = raw_probe
    else:
        probe = {"healthy": False, "error": "Unknown database probe result"}

    if probe.get("healthy"):
        health_status["components"]["database"] = {
            "status": "healthy",
            "latency_ms": probe.get("latency_ms"),
            "pool": probe.get("pool"),
            "probe_cached": probe.get("cached"),
        }
    else:
        health_status["status"] = "degraded"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": probe.get("error"),
        }

    # Check cache
    if isinstance(raw_cache, BaseException):
        cache_stats: dict[str, Any] = {
            "health": {"status": "unhealthy"},
            "error": "Cache health probe timed out"
            if isinstance(raw_cache, TimeoutError)
            else str(raw_cache),
        }
    elif isinstance(raw_cache, dict):
        cache_stats = raw_cache
    else:
        cache_stats = {"health": {"status": "unhealthy"}, "error": "Unknown cache probe result"}

    try:
        cache_health = cache_stats.get("health", {})
        if isinstance(cache_health, dict) and cache_health.get("status") == "unhealthy":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unhealthy", "cache": cache_stats},
            )
        health_status["components"]["cache"] = {"status": "healthy", **cache_stats}
    except Exception as e:
        health_status["components"]["cache"] = {"status": "unhealthy", "error": str(e)}

    # System resources are synchronous psutil calls; keep them off the event
    # loop so monitoring cannot stall request handling.
    try:
        system_metrics, process_metrics = await asyncio.to_thread(
            _get_health_system_metrics, psutil
        )
        health_status["components"]["system"] = system_metrics
        health_status["components"]["process"] = process_metrics
    except Exception:
        health_status["components"]["system"] = {"status": "unknown"}

    response_status = (
        status.HTTP_200_OK
        if health_status["status"] == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=response_status, content=health_status)


def _get_health_system_metrics(psutil_module: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Collect synchronous process/system metrics outside the event loop."""
    process = psutil_module.Process(os.getpid())
    with process.oneshot():
        disk_usage = psutil_module.disk_usage("/")
        system_metrics = {
            "cpu_percent": psutil_module.cpu_percent(),
            "memory_percent": psutil_module.virtual_memory().percent,
            "disk_percent": disk_usage.percent if hasattr(disk_usage, "percent") else 0,
        }
        process_metrics = {
            "cpu_percent": process.cpu_percent(interval=None),
            "memory_percent": process.memory_percent(),
            "rss_bytes": process.memory_info().rss,
        }
    return system_metrics, process_metrics


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    Returns metrics in Prometheus text format.
    """
    _require_metrics_enabled()
    from database import async_engine
    from middleware.monitoring import get_request_metrics
    from services.cache_service import cache_service

    metrics = []

    # HTTP request metrics (latency, count, errors)
    request_metrics = get_request_metrics()
    metrics.extend(request_metrics.get_prometheus_metrics())

    # Database pool metrics
    if async_engine:
        metrics.extend(_get_database_metrics(async_engine.pool))

    # Cache metrics
    metrics.extend(await _get_cache_metrics(cache_service))

    # System metrics
    metrics.extend(_get_system_metrics())

    # Add timestamp
    metrics.extend(
        [
            "# HELP scrape_timestamp_seconds Timestamp of metrics scrape",
            "# TYPE scrape_timestamp_seconds gauge",
            f"scrape_timestamp_seconds {time.time()}",
        ]
    )

    return PlainTextResponse(content="\n".join(metrics), media_type="text/plain")


async def _probe_database(settings: Any) -> dict[str, Any]:
    """Run or reuse a short-lived database probe for detailed health endpoints."""
    global _db_probe_cache

    ttl = float(getattr(settings, "health_check_cache_ttl_seconds", 1.0))
    now = time.monotonic()
    if _db_probe_cache and ttl > 0 and now - _db_probe_cache[0] < ttl:
        return {**_db_probe_cache[1], "cached": True}

    async with _db_probe_lock:
        now = time.monotonic()
        if _db_probe_cache and ttl > 0 and now - _db_probe_cache[0] < ttl:
            return {**_db_probe_cache[1], "cached": True}

        from sqlalchemy import text

        from database import AsyncSessionLocal, async_engine

        try:
            start = time.perf_counter()
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            result = {
                "healthy": True,
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "pool": _get_pool_stats(async_engine.pool) if async_engine else {},
                "cached": False,
            }
        except Exception as exc:
            logger.exception(f"Database health check failed: {exc}")
            result = {"healthy": False, "error": str(exc), "cached": False}

        if ttl > 0:
            _db_probe_cache = (time.monotonic(), result)
        return result


def _get_pool_stats(pool: Any) -> dict[str, int]:
    """
    Helper to get pool statistics.
    Uses Any for pool to bypass Mypy checks on internal attributes.
    """
    stats = {}
    for key, method_name in (
        ("size", "size"),
        ("checked_out", "checkedout"),
        ("overflow", "overflow"),
        ("checked_in", "checkedin"),
    ):
        method = getattr(pool, method_name, None)
        if method is not None:
            stats[key] = method()
    return stats


def _get_database_metrics(pool: Any) -> list[str]:
    """Helper to get database metrics."""
    try:
        stats = _get_pool_stats(pool)
        return [
            "# HELP db_pool_size Current database connection pool size",
            "# TYPE db_pool_size gauge",
            f"db_pool_size {stats['size']}",
            "# HELP db_pool_checked_out Number of connections currently in use",
            "# TYPE db_pool_checked_out gauge",
            f"db_pool_checked_out {stats['checked_out']}",
            "# HELP db_pool_overflow Number of overflow connections",
            "# TYPE db_pool_overflow gauge",
            f"db_pool_overflow {stats['overflow']}",
            "# HELP db_pool_checked_in Number of connections available in pool",
            "# TYPE db_pool_checked_in gauge",
            f"db_pool_checked_in {stats['checked_in']}",
        ]
    except Exception as e:
        return [f"# db_pool_error: {e}"]


async def _get_cache_metrics(cache_service: Any) -> list[str]:
    """Helper to get cache metrics."""
    metrics = []
    try:
        cache_stats = await cache_service.get_stats()
        metrics.extend(
            [
                "# HELP cache_hits_total Total number of cache hits",
                "# TYPE cache_hits_total counter",
                f"cache_hits_total {cache_stats.get('hits', 0)}",
                "# HELP cache_misses_total Total number of cache misses",
                "# TYPE cache_misses_total counter",
                f"cache_misses_total {cache_stats.get('misses', 0)}",
                "# HELP cache_sets_total Total number of cache sets",
                "# TYPE cache_sets_total counter",
                f"cache_sets_total {cache_stats.get('sets', 0)}",
                "# HELP cache_hit_rate Cache hit rate percentage",
                "# TYPE cache_hit_rate gauge",
                f"cache_hit_rate {cache_stats.get('hit_rate', 0)}",
                "# HELP cache_size Current number of items in cache",
                "# TYPE cache_size gauge",
                f"cache_size {cache_stats.get('size', 0)}",
            ]
        )

        # Redis-specific metrics
        if cache_stats.get("backend") == "redis":
            health = cache_stats.get("health", {})
            metrics.extend(
                [
                    "# HELP redis_connected Redis connection status (1=connected, 0=disconnected)",
                    "# TYPE redis_connected gauge",
                    f"redis_connected {1 if health.get('connected') else 0}",
                    "# HELP redis_latency_ms Redis ping latency in milliseconds",
                    "# TYPE redis_latency_ms gauge",
                    f"redis_latency_ms {health.get('latency_ms', 0)}",
                ]
            )
    except Exception as e:
        metrics.append(f"# cache_error: {e}")

    return metrics


def _get_system_metrics() -> list[str]:
    """Return process-scoped resource metrics for this worker."""
    metrics = []
    try:
        import psutil

        process = psutil.Process(os.getpid())
        with process.oneshot():
            cpu_percent = process.cpu_percent(interval=None)
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

        metrics.extend(
            [
                "# HELP process_cpu_percent CPU usage percentage for this worker",
                "# TYPE process_cpu_percent gauge",
                f"process_cpu_percent {cpu_percent}",
                "# HELP process_memory_percent Memory usage percentage for this worker",
                "# TYPE process_memory_percent gauge",
                f"process_memory_percent {memory_percent}",
                "# HELP process_resident_memory_bytes Resident memory for this worker",
                "# TYPE process_resident_memory_bytes gauge",
                f"process_resident_memory_bytes {memory_info.rss}",
            ]
        )
    except ImportError:
        metrics.append("# psutil not installed, system metrics unavailable")
    except Exception as e:
        metrics.append(f"# system_error: {e}")

    return metrics
