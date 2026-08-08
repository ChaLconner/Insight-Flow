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
import time

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from services.cache_service import cache_service

logger = logging.getLogger(__name__)


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

    # Try to use Redis if configured
    redis_url = settings.cache.redis_url

    if redis_url and settings.is_production:
        try:
            # Test Redis connection
            import redis

            r = redis.from_url(redis_url)
            r.ping()

            logger.info(f"Rate limiter using Redis: {redis_url[:20]}...")
            return Limiter(
                key_func=get_user_identifier,
                storage_uri=redis_url,
                strategy="fixed-window",
            )
        except Exception as e:
            logger.critical(
                f"Redis connection FAILED for SlowAPI rate limiting: {e}. "
                "Falling back to in-memory storage — NOT suitable for production "
                "multi-worker deployments! Rate limits will NOT be shared across workers."
            )

    # Fallback to in-memory storage
    if settings.is_production:
        logger.warning(
            "Using in-memory rate limiting in production - "
            "rate limits won't be shared across workers. "
            "Configure REDIS_URL for distributed rate limiting."
        )
    else:
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
            "X-RateLimit-Limit": request.state.view_rate_limit
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

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        key = f"rate_limit:{client_ip}:{path}"

        # Get current usage
        usage_data = await self.cache_service.get(key)
        current_time = time.time()

        if usage_data:
            count = usage_data["content"]["count"]
            start_time = usage_data["content"]["start_time"]

            # Check if window expired
            if current_time - start_time > self.window:
                # Reset
                await self.cache_service.set(
                    key, {"content": {"count": 1, "start_time": current_time}}, timeout=self.window
                )
            else:
                # Increment
                if count >= self.requests:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests. Please try again later.",
                    )

                await self.cache_service.set(
                    key,
                    {"content": {"count": count + 1, "start_time": start_time}},
                    timeout=self.window,
                )
        else:
            # First request
            await self.cache_service.set(
                key, {"content": {"count": 1, "start_time": current_time}}, timeout=self.window
            )


# Pre-configured auth rate limiter instance
auth_rate_limiter = AuthRateLimiter(requests=5, window=60)  # 5 requests per minute
