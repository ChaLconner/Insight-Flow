"""
Route-level rate limiting configuration (SlowAPI decorator-based).

This module provides per-endpoint rate limits applied via decorators on individual
router handlers (e.g., auth, payment). It is **complementary** to the global
middleware rate limiters in ``middleware/rate_limit.py`` (in-memory fallback) and
``middleware/redis_rate_limit.py`` (Redis, production).

Architecture:
    - Global middleware (``middleware_config.setup_rate_limit_middleware``) → broad DDoS protection
    - This module (``@limiter.limit()``, ``AuthRateLimiter``) → fine-grained per-route limits

Production: Uses Redis for distributed rate limiting across multiple workers.
Development: Falls back to in-memory storage for simplicity.
"""

import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from services.cache_service import cache_service
from utils.request_security import get_client_ip

logger = logging.getLogger(__name__)


def get_remote_address(request: Request) -> str:
    """Compatibility wrapper that now uses the trusted-proxy IP parser."""
    return get_client_ip(request)


def get_user_identifier(request: Request) -> str:
    """
    Get user identifier for rate limiting.
    Uses authenticated user ID if available, otherwise falls back to IP address.
    """
    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Fallback to IP address
    return get_remote_address(request)


def create_limiter() -> Limiter:
    """
    Create rate limiter with Redis storage for production,
    falling back to in-memory for development.
    """
    from config import get_settings

    settings = get_settings()

    redis_url = settings.cache.redis_url

    if settings.is_production and not redis_url:
        raise RuntimeError("REDIS_URL is required in production for distributed rate limiting.")

    if redis_url:
        try:
            # Test Redis connection
            import redis

            r = redis.from_url(redis_url)
            r.ping()

            logger.info("Rate limiter using Redis-backed distributed storage")
            return Limiter(
                key_func=get_user_identifier,
                storage_uri=redis_url,
                strategy="fixed-window",
            )
        except Exception as e:
            if settings.is_production:
                raise RuntimeError("Redis-backed rate limiting is required in production.") from e
            logger.warning(f"Redis connection failed; using development-only in-memory limits: {e}")

    # Fallback to in-memory storage
    if not settings.is_production:
        logger.info("Using in-memory rate limiting (development mode)")

    return Limiter(key_func=get_user_identifier)


# Create limiter instance
limiter = create_limiter()


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors."""
    # Log the rate limit hit
    logger.warning(
        f"Rate limit exceeded: {get_user_identifier(request)} "
        f"on {request.method} {request.url.path}"
    )

    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": exc.detail,
            "error_code": "RATE_LIMIT_EXCEEDED",
        },
        headers={
            "Retry-After": str(exc.detail),
            "X-RateLimit-Limit": str(request.state.view_rate_limit)
            if hasattr(request.state, "view_rate_limit")
            else "unknown",
        },
    )


# Rate limit configurations for different endpoint types
class RateLimits:
    """
    Centralized rate limit configurations.
    All limits are defined here for easy adjustment.

    Format: "X/period" where period is: second, minute, hour, day

    Production recommendations:
    - Use stricter limits for financial operations
    - Consider IP-based limiting for unauthenticated endpoints
    - Monitor and adjust based on actual usage patterns
    """

    # Payment & Financial endpoints (most restrictive)
    PAYMENT_SETUP_INTENT = "5/minute"  # Creating setup intents
    PAYMENT_ADD_METHOD = "10/minute"  # Adding payment methods
    PAYMENT_SUBSCRIPTION = "5/minute"  # Subscription operations
    PAYMENT_DELETE = "10/minute"  # Deleting payment methods

    # General payment reads (more lenient)
    PAYMENT_READ = "60/minute"  # Reading payment data

    # Authentication (prevent brute force)
    AUTH_LOGIN = "10/minute"  # Login attempts
    AUTH_REGISTER = "5/minute"  # Registration
    AUTH_PASSWORD_RESET = "3/minute"  # Password reset requests

    # General API endpoints
    API_READ = "200/minute"  # General read operations
    API_WRITE = "60/minute"  # General write operations

    # Webhooks (from Stripe) - high limit
    WEBHOOK = "300/minute"  # Webhook processing
    CSP_REPORT = "30/minute"  # Public CSP telemetry, bounded by body size

    # Stricter limits for known abuse vectors
    SENSITIVE_READ = "30/minute"  # Sensitive data access
    BULK_OPERATIONS = "20/minute"  # Bulk create/update/delete

    # Analytics & Dashboard (expensive DB aggregation queries)
    ANALYTICS_READ = "30/minute"  # Analytics overview, contributions
    ANALYTICS_BATCH = "10/minute"  # Batch activity queries (amplification risk)
    DASHBOARD_READ = "30/minute"  # Dashboard overview (parallel queries)

    # Task management
    TASK_CREATE = "30/minute"  # Task creation (triggers notifications)
    TASK_UPDATE = "60/minute"  # Task updates
    TASK_DELETE = "20/minute"  # Task deletion

    # Notifications (prevent rapid polling abuse)
    NOTIFICATION_POLL = "60/minute"  # List/count notifications
    NOTIFICATION_BULK = "10/minute"  # Bulk read operations

    # Favorites (write operations)
    FAVORITES_WRITE = "30/minute"  # Toggle/add/remove favorites

    # Project management
    PROJECT_CREATE = "10/minute"  # Project creation
    PROJECT_UPDATE = "30/minute"  # Project updates
    PROJECT_DELETE = "10/minute"  # Project deletion
    PROJECT_MEMBERS = "20/minute"  # Member management (add/remove)

    # User management
    USER_SEARCH = "30/minute"  # User search
    USER_PROFILE_UPDATE = "20/minute"  # Profile updates
    USER_AVATAR = "5/minute"  # Avatar upload (file processing)


# =============================================================================
# Async Rate Limiter for FastAPI Dependencies (e.g., auth routes)
# Uses cache_service for rate limiting with async support
# =============================================================================


class AuthRateLimiter:
    """
    Async rate limiter for use as FastAPI dependency.
    Uses cache_service for storage, supporting both Redis and in-memory backends.
    """

    def __init__(self, requests: int = 5, window: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests: Maximum number of requests allowed in the window
            window: Time window in seconds
        """
        self.requests = requests
        self.window = window
        self.cache_service = cache_service

    async def __call__(self, request: Request):
        """
        Check rate limit for the request.
        Raises HTTPException if limit exceeded.
        """
        # Skip rate limiting in testing mode
        from config import get_settings

        settings = get_settings()
        if settings.is_testing:
            return

        if settings.is_production and not await self.cache_service.ensure_connected():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting service unavailable. Please retry shortly.",
            )

        client_ip = get_client_ip(request)
        path = request.url.path

        key = f"rate_limit:{client_ip}:{path}"
        try:
            count = await self.cache_service.increment_with_window(
                key,
                self.window,
                fail_closed=settings.is_production,
            )
        except Exception as exc:
            logger.error("Rate-limit counter unavailable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting service unavailable. Please retry shortly.",
            ) from exc

        if count > self.requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )


# Pre-configured auth rate limiter instance
auth_rate_limiter = AuthRateLimiter(requests=5, window=60)  # 5 requests per minute
