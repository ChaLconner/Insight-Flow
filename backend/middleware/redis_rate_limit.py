"""
Redis-based rate limiting middleware for distributed environments (production).

Used by ``core/middleware_config.py`` as the primary global rate limiter when Redis
is available. Falls back to ``middleware/rate_limit.py`` (in-memory) otherwise.
For fine-grained per-route limits, see ``rate_limiter.py`` (SlowAPI-based).
"""

import time
import uuid

from fastapi import Request
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

from middleware.rate_limit import RATE_LIMIT_CONFIG, get_rate_limit_for_path
from utils.logger import setup_logger
from utils.request_security import get_client_ip

logger = setup_logger("redis_rate_limit")


class RedisRateLimitMiddleware:
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
        fail_closed: bool = False,
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
        self.app = app
        self.calls = calls
        self.period = period
        self.key_prefix = key_prefix
        self.redis_client = redis_client
        self.skip_paths = skip_paths or ["/static", "/", "/health", "/metrics"]
        self.fail_closed = fail_closed
        logger.info(f"Redis rate limiting initialized: {calls} requests per {period}s")

    def _is_skipped_path(self, path: str) -> bool:
        """Return whether *path* is an explicitly configured exempt route.

        Exemptions are path-segment aware.  In particular, ``/`` is only the
        root route; treating it as a prefix would exempt every HTTP request.
        """
        for exempt_path in self.skip_paths:
            normalized = exempt_path.rstrip("/") or "/"
            if normalized == "/":
                if path == "/":
                    return True
            elif path == normalized or path.startswith(f"{normalized}/"):
                return True
        return False

    def _get_rate_limit_key(self, request: Request) -> tuple[str, int, int]:
        """
        Generate a unique rate limit key for the request and get rate limits.

        Returns:
            Tuple of (key, calls, period)
        """
        client_ip = get_client_ip(request)
        path = request.url.path

        # Normalize path (remove query parameters)
        path = path.split("?")[0]

        # Get rate limit for this path
        calls, period = get_rate_limit_for_path(path, self.calls, self.period)

        # Check if this path has a specific rate limit
        rate_key_path = path
        for prefix in RATE_LIMIT_CONFIG:
            if path.startswith(prefix):
                rate_key_path = prefix
                break

        return f"{self.key_prefix}:{client_ip}:{rate_key_path}", calls, period

    async def _check_rate_limit(self, key: str, calls: int, period: int) -> tuple[bool, int]:
        """
        Check if the request should be rate limited using sliding window algorithm.

        Args:
            key: Redis key for rate limiting
            calls: Maximum number of calls allowed
            period: Time period in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = time.time()
        window_start = now - period
        member_id = f"{now}:{uuid.uuid4().hex[:8]}"

        try:
            pipe = self.redis_client.pipeline(transaction=True)
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {member_id: now})
            pipe.zcard(key)
            pipe.expire(key, period + 1)

            res = pipe.execute()
            if hasattr(res, "__await__"):
                results = await res
            else:
                results = res

            current_count = results[2]
            remaining = max(0, calls - current_count)
            is_allowed = current_count <= calls

            return is_allowed, remaining

        except Exception as e:
            logger.exception(f"Redis rate limit check failed: {e}")
            if self.fail_closed:
                return False, -1
            # Development fallback: allow request if Redis fails.
            return True, calls

    async def __call__(self, scope, receive, send):
        """
        Process request with rate limiting.

        Skips rate limiting for:
        - Static files
        - Health check endpoints
        - Metrics endpoints
        - Paths in skip_paths
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        # Skip rate limiting for certain paths
        if self._is_skipped_path(path):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Get rate limit key and limits for this request
        key, calls, period = self._get_rate_limit_key(request)

        # Check rate limit
        is_allowed, remaining = await self._check_rate_limit(key, calls, period)

        if remaining < 0:
            response = JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "message": "Rate limiting service unavailable. Please retry shortly.",
                    "code": "RATE_LIMIT_UNAVAILABLE",
                },
                headers={"Retry-After": "5"},
            )
            await response(scope, receive, send)
            return

        if not is_allowed:
            client_info = scope.get("client")
            client_host = client_info[0] if client_info else "unknown"
            logger.warning(
                f"Rate limit exceeded for {client_host} on {path} (limit: {calls}/{period}s)"
            )
            response = JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Too many requests. Please try again later.",
                    "code": "RATE_LIMIT_EXCEEDED",
                },
                headers={
                    "Retry-After": str(period),
                    "X-RateLimit-Limit": str(calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + period)),
                },
            )
            await response(scope, receive, send)
            return

        # Process request and add headers
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-RateLimit-Limit", str(calls))
                headers.append("X-RateLimit-Remaining", str(remaining))
                headers.append("X-RateLimit-Reset", str(int(time.time() + period)))
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RedisRateLimiter:
    """
    Helper class for Redis-based rate limiting without middleware.
    Can be used in route handlers for custom rate limiting.
    """

    def __init__(self, redis_client, key_prefix: str = "rate_limit"):
        self.redis_client = redis_client
        self.key_prefix = key_prefix

    async def check(self, identifier: str, calls: int, period: int) -> tuple[bool, int]:
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
        member_id = f"{now}:{uuid.uuid4().hex[:8]}"

        try:
            pipe = self.redis_client.pipeline(transaction=True)
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {member_id: now})
            pipe.zcard(key)
            pipe.expire(key, period + 1)

            res = pipe.execute()
            if hasattr(res, "__await__"):
                results = await res
            else:
                results = res

            current_count = results[2]
            remaining = max(0, calls - current_count)
            is_allowed = current_count <= calls

            return is_allowed, remaining

        except Exception as e:
            logger.exception(f"Redis rate limit check failed: {e}")
            return True, calls

    async def reset(self, identifier: str) -> bool:
        """
        Reset rate limit for a given identifier.

        Args:
            identifier: Unique identifier to reset

        Returns:
            True if reset was successful
        """
        key = f"{self.key_prefix}:{identifier}"
        try:
            res = self.redis_client.delete(key)
            if hasattr(res, "__await__"):
                await res
            return True
        except Exception as e:
            logger.exception(f"Failed to reset rate limit: {e}")
            return False
