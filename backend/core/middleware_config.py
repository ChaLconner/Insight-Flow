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
        expose_headers=[
            "Retry-After",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Request-ID",
            "X-Response-Time",
        ],
    )


def setup_trusted_host_middleware(app: FastAPI) -> None:
    """Configure trusted host middleware for security."""
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)


def setup_rate_limit_middleware(app: FastAPI) -> None:
    """
    Configure rate limiting middleware.
    Uses Redis if available, falls back to in-memory.

    SECURITY NOTE (VULN-01): In-memory rate limiting is NOT safe for
    production multi-worker deployments. Each worker maintains its own
    counter, effectively multiplying the allowed rate by N workers.
    """
    from middleware.rate_limit import RateLimitMiddleware
    from middleware.redis_rate_limit import RedisRateLimitMiddleware

    # Disable rate limiting in tests
    if settings.is_testing:
        logger.info("Skipping rate limit middleware in testing environment")
        return

    if settings.is_production and not settings.cache.redis_url:
        raise RuntimeError("REDIS_URL is required in production for distributed rate limiting.")

    if settings.cache.redis_url:
        try:
            from services.cache_service import cache_service

            if hasattr(cache_service.backend, "client"):
                app.add_middleware(
                    RedisRateLimitMiddleware,
                    redis_client=cache_service.backend.client,
                    calls=200,
                    period=60,
                    fail_closed=settings.is_production,
                )
                logger.info("Using Redis-based rate limiting")
                return
            if settings.is_production:
                raise RuntimeError("Configured Redis backend is unavailable for rate limiting.")
        except Exception as e:
            if settings.is_production:
                raise RuntimeError("Redis-backed rate limiting is required in production.") from e
            logger.warning(f"Redis rate limiting failed, falling back to in-memory: {e}")

    # VULN-01: Development-only fallback. Production fails during app setup.
    if settings.is_production:
        logger.critical(
            "⚠️ SECURITY WARNING: Using in-memory rate limiting in production! "
            "Rate limits will NOT be shared across workers. "
            "An attacker gets N x the configured limit (where N = worker count). "
            "Configure REDIS_URL for distributed rate limiting."
        )

    # Fallback to in-memory rate limiting
    app.add_middleware(RateLimitMiddleware, calls=200, period=60)
    if settings.cache.redis_url:
        logger.info("Using in-memory rate limiting (Redis not connected)")
    else:
        logger.info("Using in-memory rate limiting (Redis not configured)")


def setup_request_body_limit_middleware(app: FastAPI) -> None:
    """Cap untrusted report/webhook bodies before JSON parsing."""
    from middleware.request_body_limit import RequestBodyLimitMiddleware

    app.add_middleware(
        RequestBodyLimitMiddleware,
        limits={
            "/api/v1/security/csp-report": 64 * 1024,
            "/api/v1/payment/webhook": 256 * 1024,
        },
    )


def setup_csrf_middleware(app: FastAPI) -> None:
    """
    Configure CSRF protection middleware.
    Uses double-submit cookie pattern for CSRF protection.
    """
    from middleware.csrf import CSRFMiddleware

    # Skip CSRF in testing environment
    if settings.is_testing:
        logger.info("Skipping CSRF middleware in testing environment")
        return

    # In development, use less strict settings
    cookie_secure = settings.is_production

    app.add_middleware(
        CSRFMiddleware,
        enabled=True,
        cookie_secure=cookie_secure,
    )
    logger.info(f"CSRF middleware enabled (secure cookies: {cookie_secure})")


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
    from middleware.response_cache import ResponseCacheMiddleware

    app.add_middleware(ResponseCacheMiddleware)  # API Cache-Control headers
    # Note: Server-side response caching is handled at the service layer
    # (e.g., cache_service in dashboard/analytics services) for proper
    # cache invalidation. The removed CacheMiddleware was a no-op since
    # it excluded all major routes (/tasks, /projects, /users, etc.).


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

    # Request body limits must wrap parsing and run before route handlers.
    setup_request_body_limit_middleware(app)

    # CSRF protection
    setup_csrf_middleware(app)

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
