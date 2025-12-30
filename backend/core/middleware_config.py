"""
Middleware configuration module.
Centralizes all middleware setup for the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger("middleware_config")
settings = get_settings()


def setup_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware with settings from config."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins_list,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
        expose_headers=["*"],
    )


def setup_trusted_host_middleware(app: FastAPI) -> None:
    """Configure trusted host middleware for security."""
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)


def setup_rate_limit_middleware(app: FastAPI) -> None:
    """
    Configure rate limiting middleware.
    Uses Redis if available, falls back to in-memory.
    """
    from middleware.rate_limit import RateLimitMiddleware
    from middleware.redis_rate_limit import RedisRateLimitMiddleware

    # Disable rate limiting in tests
    if settings.is_testing:
        logger.info("Skipping rate limit middleware in testing environment")
        return

    if settings.cache.redis_url:
        try:
            from services.cache_service import cache_service

            if hasattr(cache_service.backend, "client"):
                app.add_middleware(
                    RedisRateLimitMiddleware,
                    redis_client=cache_service.backend.client,
                    calls=200,
                    period=60,
                )
                logger.info("Using Redis-based rate limiting")
                return
        except Exception as e:
            logger.warning(f"Redis rate limiting failed, falling back to in-memory: {e}")

    # Fallback to in-memory rate limiting
    app.add_middleware(RateLimitMiddleware, calls=200, period=60)
    if settings.cache.redis_url:
        logger.info("Using in-memory rate limiting (Redis not connected)")
    else:
        logger.info("Using in-memory rate limiting (Redis not configured)")


def setup_security_middleware(app: FastAPI) -> None:
    """Configure security-related middleware."""
    from middleware.security_headers import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware)


def setup_performance_middleware(app: FastAPI) -> None:
    """Configure performance monitoring middleware."""
    from middleware.monitoring import PerformanceMiddleware

    app.add_middleware(PerformanceMiddleware)


def setup_cache_middleware(app: FastAPI) -> None:
    """Configure caching middleware."""
    from middleware.cache import CacheMiddleware
    from middleware.response_cache import ResponseCacheMiddleware

    app.add_middleware(ResponseCacheMiddleware)  # API Cache-Control headers
    app.add_middleware(CacheMiddleware, cache_timeout=60)


def setup_request_id_middleware(app: FastAPI) -> None:
    """Configure request ID middleware for tracing."""
    from middleware.request_id import RequestIDMiddleware

    app.add_middleware(RequestIDMiddleware)


def setup_compression_middleware(app: FastAPI) -> None:
    """Configure response compression middleware."""
    app.add_middleware(GZipMiddleware, minimum_size=1500)


def setup_all_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the application.
    Order matters - middleware is executed in reverse order of addition.
    """
    # Compression (outermost - runs last on request, first on response)
    setup_compression_middleware(app)

    # Rate limiting
    setup_rate_limit_middleware(app)

    # Security headers
    setup_security_middleware(app)

    # Caching
    setup_cache_middleware(app)

    # Performance monitoring
    setup_performance_middleware(app)

    # Request ID for tracing
    setup_request_id_middleware(app)

    # Trusted hosts (security)
    setup_trusted_host_middleware(app)

    # CORS (innermost - runs first on request)
    setup_cors_middleware(app)

    logger.info("All middleware configured successfully")
