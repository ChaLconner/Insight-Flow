"""
Health check router for monitoring and observability.
Provides endpoints for Kubernetes liveness/readiness probes and general health monitoring.
"""

import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger("health_router")
settings = get_settings()

router = APIRouter(tags=["health"])


@router.get("/")
def read_root():
    """Root endpoint - basic API info."""
    return {"message": "Hello from FastAPI", "version": settings.api_version}


@router.get("/minimal-test")
def minimal_test():
    """Minimal test endpoint to check if FastAPI is responsive."""
    return {"status": "success", "message": "Minimal test working"}


@router.get("/test-auth")
def test_auth():
    """Test endpoint to check authentication."""
    return {"message": "Auth test endpoint"}


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    Returns overall application health status.
    """
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": settings.api_version,
    }


@router.get("/health/db")
async def db_health_check():
    """
    Database health check with connection pool statistics.
    Useful for monitoring and debugging connection issues.
    """
    from sqlalchemy import text

    from database import AsyncSessionLocal, async_engine

    try:
        # Test async database connection
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        # Get pool statistics
        pool_stats = _get_pool_stats(async_engine.pool)

        return {
            "status": "healthy",
            "database": "connected",
            "async_pool": {
                **pool_stats,
                "pool_size": settings.database.pool_size,
                "max_overflow": settings.database.max_overflow,
            },
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/health/cache")
async def cache_health_check():
    """
    Cache health check with statistics.
    """
    from services.cache_service import cache_service

    try:
        stats = cache_service.get_stats()
        return {"status": "healthy", "cache": stats}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health/full")
async def full_health_check():
    """
    Comprehensive health check for all system components.
    Useful for Kubernetes liveness/readiness probes.
    """
    import psutil
    from sqlalchemy import text

    from database import AsyncSessionLocal, async_engine
    from services.cache_service import cache_service

    health_status: dict[str, Any] = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.environment,
        "version": settings.api_version,
        "components": {},
    }

    # Check database
    try:
        start = time.time()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_latency = round((time.time() - start) * 1000, 2)

        health_status["components"]["database"] = {
            "status": "healthy",
            "latency_ms": db_latency,
            "pool": _get_pool_stats(async_engine.pool),
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["database"] = {"status": "unhealthy", "error": str(e)}

    # Check cache
    try:
        cache_stats = cache_service.get_stats()
        health_status["components"]["cache"] = {"status": "healthy", **cache_stats}
    except Exception as e:
        health_status["components"]["cache"] = {"status": "unhealthy", "error": str(e)}

    # System resources
    try:
        health_status["components"]["system"] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent
            if hasattr(psutil.disk_usage("/"), "percent")
            else 0,
        }
    except Exception:
        health_status["components"]["system"] = {"status": "unknown"}

    return health_status


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    Returns metrics in Prometheus text format.
    """
    from database import async_engine
    from services.cache_service import cache_service

    metrics = []

    # Database pool metrics
    metrics.extend(_get_database_metrics(async_engine.pool))

    # Cache metrics
    metrics.extend(_get_cache_metrics(cache_service))

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


def _get_pool_stats(pool: Any) -> dict[str, int]:
    """
    Helper to get pool statistics.
    Uses Any for pool to bypass Mypy checks on internal attributes.
    """
    return {
        "size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
    }


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


def _get_cache_metrics(cache_service: Any) -> list[str]:
    """Helper to get cache metrics."""
    metrics = []
    try:
        cache_stats = cache_service.get_stats()
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
    """Helper to get system metrics."""
    metrics = []
    try:
        import psutil

        metrics.extend(
            [
                "# HELP process_cpu_percent CPU usage percentage",
                "# TYPE process_cpu_percent gauge",
                f"process_cpu_percent {psutil.cpu_percent()}",
                "# HELP process_memory_percent Memory usage percentage",
                "# TYPE process_memory_percent gauge",
                f"process_memory_percent {psutil.virtual_memory().percent}",
            ]
        )
    except ImportError:
        metrics.append("# psutil not installed, system metrics unavailable")
    except Exception as e:
        metrics.append(f"# system_error: {e}")

    return metrics
