"""
Redis-based rate limiting middleware for distributed rate limiting.
Uses sliding window algorithm with Redis for distributed environments.
"""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from utils.logger import setup_logger

logger = setup_logger("redis_rate_limit")


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-based rate limiting middleware using sliding window algorithm.

    Features:
    - Distributed rate limiting across multiple instances
    - Sliding window for accurate rate limiting
    - Automatic cleanup of old entries via Redis TTL
    - Configurable limits per endpoint
    - Rate limit headers in responses
    """

    def __init__(
        self,
        app,
        redis_client,
        calls: int = 100,
        period: int = 60,
        key_prefix: str = "rate_limit",
        skip_paths: list | None = None,
    ):
        """
        Initialize Redis rate limiting middleware.

        Args:
            app: FastAPI application
            redis_client: Redis client instance
            calls: Maximum number of requests allowed in the period
            period: Time period in seconds
            key_prefix: Prefix for Redis keys
            skip_paths: List of paths to skip rate limiting for
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.key_prefix = key_prefix
        self.redis_client = redis_client
        self.skip_paths = skip_paths or ["/static", "/", "/health", "/metrics"]

        # Validate Redis connection
        try:
            self.redis_client.ping()
            logger.info(f"Redis rate limiting initialized: {calls} requests per {period}s")
        except Exception as e:
            logger.error(f"Redis connection failed for rate limiting: {e}")
            raise RuntimeError("Redis is required for distributed rate limiting")

    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Generate a unique rate limit key for the request.

        Key format: {prefix}:{client_ip}:{path}
        """
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Normalize path (remove query parameters)
        path = path.split("?")[0]

        # Use a shorter path for rate limiting (group similar endpoints)
        # For example: /api/v1/projects/123 -> /api/v1/projects/*
        parts = path.split("/")
        if len(parts) > 4 and parts[3].isdigit():
            parts[3] = "*"
            path = "/".join(parts)

        return f"{self.key_prefix}:{client_ip}:{path}"

    def _check_rate_limit(self, key: str) -> tuple[bool, int]:
        """
        Check if the request should be rate limited using sliding window algorithm.

        Args:
            key: Redis key for rate limiting

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = time.time()
        window_start = now - self.period

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in the window
            pipe.zcard(key)

            # Add current request timestamp
            pipe.zadd(key, {str(now): now})

            # Set TTL to period + 1 second buffer
            pipe.expire(key, self.period + 1)

            # Execute pipeline
            results = pipe.execute()

            # results[1] is the count after removing old entries
            current_count = results[1]
            remaining = max(0, self.calls - current_count)

            is_allowed = current_count <= self.calls

            return is_allowed, remaining

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fail open: allow request if Redis fails
            return True, self.calls

    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.

        Skips rate limiting for:
        - Static files
        - Health check endpoints
        - Metrics endpoints
        - Paths in skip_paths
        """
        # Skip rate limiting for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)

        # Get rate limit key
        key = self._get_rate_limit_key(request)

        # Check rate limit
        is_allowed, remaining = self._check_rate_limit(key)

        if not is_allowed:
            client_host = request.client.host if request.client else "unknown"
            logger.warning(f"Rate limit exceeded for {client_host} on {request.url.path}")
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Too many requests. Please try again later.",
                    "code": "RATE_LIMIT_EXCEEDED",
                },
                headers={
                    "Retry-After": str(self.period),
                    "X-RateLimit-Limit": str(self.calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + self.period)),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.period))

        return response


class RedisRateLimiter:
    """
    Helper class for Redis-based rate limiting without middleware.
    Can be used in route handlers for custom rate limiting.
    """

    def __init__(self, redis_client, key_prefix: str = "rate_limit"):
        self.redis_client = redis_client
        self.key_prefix = key_prefix

    def check(self, identifier: str, calls: int, period: int) -> tuple[bool, int]:
        """
        Check rate limit for a given identifier.

        Args:
            identifier: Unique identifier (e.g., user_id, ip_address)
            calls: Maximum number of requests allowed
            period: Time period in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        key = f"{self.key_prefix}:{identifier}"
        now = time.time()
        window_start = now - period

        try:
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, period + 1)
            results = pipe.execute()

            current_count = results[1]
            remaining = max(0, calls - current_count)
            is_allowed = current_count <= calls

            return is_allowed, remaining

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return True, calls

    def reset(self, identifier: str) -> bool:
        """
        Reset rate limit for a given identifier.

        Args:
            identifier: Unique identifier to reset

        Returns:
            True if reset was successful
        """
        key = f"{self.key_prefix}:{identifier}"
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False
