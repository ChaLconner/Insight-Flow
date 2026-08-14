"""
In-memory rate limiting middleware for FastAPI (fallback when Redis is unavailable).

Used by ``core/middleware_config.py`` as the fallback global rate limiter.
For fine-grained per-route limits, see ``rate_limiter.py`` (SlowAPI-based).
"""

import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import Request
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

from database import AsyncSessionLocal
from services.security_log_service import SecurityLogService
from utils.request_security import get_client_ip

logger = logging.getLogger("rate_limit")

if TYPE_CHECKING:
    from asyncio import Task

# Per-endpoint rate limit configuration
# Format: path_prefix -> (calls, period_seconds)
RATE_LIMIT_CONFIG = {
    # Auth endpoints - stricter limits to prevent brute force
    "/auth/login": (10, 60),  # 10 attempts per minute
    "/auth/register": (5, 60),  # 5 registrations per minute
    "/auth/forgot-password": (3, 60),  # 3 attempts per minute
    "/auth/reset-password": (5, 60),  # 5 attempts per minute
    "/api/v1/auth/login": (10, 60),
    "/api/v1/auth/register": (5, 60),
    "/api/v1/auth/forgot-password": (3, 60),
    "/api/v1/auth/reset-password": (5, 60),
    # CSP telemetry is intentionally public for browser reports; keep its
    # ingestion budget below the generic API fallback in every rate-limit
    # backend, including the Redis path.
    "/api/v1/security/csp-report": (30, 60),
    # Private file uploads perform disk I/O and must not inherit the broad
    # generic API budget.
    "/api/v1/files/upload": (10, 60),
    # Payment endpoints - moderate limits
    "/payment": (20, 60),  # 20 requests per minute
    "/api/v1/payment": (20, 60),
}


def get_rate_limit_for_path(path: str, default_calls: int, default_period: int) -> tuple[int, int]:
    """
    Get rate limit configuration for a given path.

    Args:
        path: Request path
        default_calls: Default number of calls allowed
        default_period: Default period in seconds

    Returns:
        Tuple of (calls, period)
    """
    # Check for exact match first
    if path in RATE_LIMIT_CONFIG:
        return RATE_LIMIT_CONFIG[path]

    # Check for prefix match
    for prefix, limits in RATE_LIMIT_CONFIG.items():
        if path.startswith(prefix):
            return limits

    return (default_calls, default_period)


class RateLimitMiddleware:
    # Maximum number of IPs to track before forcing cleanup
    MAX_TRACKED_IPS = 10000
    # Cleanup interval in seconds
    CLEANUP_INTERVAL = 300  # 5 minutes
    MAX_BACKGROUND_TASKS = 1_000
    MAX_RATE_LIMIT_LOG_KEYS = 10_000

    def __init__(self, app, calls: int = 100, period: int = 60):
        self.app = app
        self.calls = calls
        self.period = period
        # Dictionary to store request timestamps per IP per path
        # Key format: "{ip}:{rate_key}" where rate_key groups similar paths
        self.request_history: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_cleanup = time.time()
        self.background_tasks: set[Task[object]] = set()
        # B8: In-memory cache for IP block status to avoid DB hit per request
        # Format: {ip: (is_blocked, blocked_until, cache_expire_time)}
        self._ip_block_cache: dict[str, tuple[bool, object, float]] = {}
        self._ip_block_cache_ttl = 30  # seconds
        self._rate_limit_log_cache: dict[str, float] = {}

    def _get_rate_key(self, request: Request) -> str:
        """Get rate limiting key for the request."""
        client_ip = get_client_ip(request)
        path = request.url.path

        # Check if this path has a specific rate limit
        for prefix in RATE_LIMIT_CONFIG:
            if path.startswith(prefix):
                return f"{client_ip}:{prefix}"

        # Default: use IP only for general rate limiting
        return f"{client_ip}:default"

    @staticmethod
    def _blocked_response(remaining: int) -> JSONResponse:
        """Build the response returned for a temporarily blocked IP."""
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "message": "Access temporarily blocked due to suspicious activity.",
                "code": "IP_BLOCKED",
                "retry_after": remaining,
            },
            headers={"Retry-After": str(remaining)},
        )

    @staticmethod
    def _remaining_block_time(blocked_until) -> int:
        """Return the number of seconds remaining on an IP block."""
        if not blocked_until:
            return 0
        return int((blocked_until - datetime.now(UTC)).total_seconds())

    def _get_cached_ip_block(
        self, client_ip: str, now_ts: float
    ) -> tuple[bool, JSONResponse | None]:
        """Return whether a valid cache entry exists and its blocked response."""
        cached = self._ip_block_cache.get(client_ip)
        if not cached:
            return False, None

        is_blocked, blocked_until, expire_at = cached
        if now_ts >= expire_at:
            del self._ip_block_cache[client_ip]
            return False, None
        if not is_blocked:
            return True, None
        remaining = self._remaining_block_time(blocked_until)
        return True, self._blocked_response(remaining)

    async def _log_blocked_access(self, request: Request, client_ip: str, remaining: int) -> None:
        """Log a blocked request without masking the block response."""
        try:
            async with AsyncSessionLocal() as db:
                await SecurityLogService.log_event(
                    db=db,
                    event_type="ip_bound_blocked_access",
                    severity="warning",
                    details={"retry_after": remaining, "reason": "IP Blocked"},
                    request=request,
                    ip_address=client_ip,
                )
        except Exception as e:
            logger.exception(f"Failed to log blocked access: {e}")

    def _should_log_rate_limit_violation(
        self, client_ip: str, path: str, period: int, now: float
    ) -> bool:
        """Sample one security-log write per IP/path/window without awaiting it."""
        key = f"{client_ip}:{path}"
        with self._lock:
            last_logged = self._rate_limit_log_cache.get(key)
            if last_logged is not None and now - last_logged < period:
                return False

            if len(self._rate_limit_log_cache) >= self.MAX_RATE_LIMIT_LOG_KEYS:
                oldest_key = min(
                    self._rate_limit_log_cache,
                    key=lambda cache_key: self._rate_limit_log_cache[cache_key],
                )
                self._rate_limit_log_cache.pop(oldest_key, None)
            self._rate_limit_log_cache[key] = now
            return True

    async def _log_rate_limit_violation(
        self,
        request: Request,
        client_ip: str,
        path: str,
        calls: int,
        period: int,
    ) -> None:
        """Persist sampled rate-limit telemetry outside the request path."""
        try:
            async with AsyncSessionLocal() as db:
                await SecurityLogService.log_event(
                    db=db,
                    event_type="rate_limit_exceeded",
                    severity="warning",
                    details={"limit": calls, "period": period, "path": path},
                    request=request,
                    ip_address=client_ip,
                )
        except Exception as e:
            logger.exception(f"Failed to log rate limit: {e}")

    async def _build_blocked_ip_response(
        self, request: Request, client_ip: str, blocked_until
    ) -> JSONResponse:
        """Log and build a response for a block fetched from the blocker."""
        remaining = self._remaining_block_time(blocked_until)
        logger.warning(f"Blocked IP {client_ip} attempted access")
        await self._log_blocked_access(request, client_ip, remaining)
        return self._blocked_response(remaining)

    async def _check_ip_block(self, request: Request, client_ip: str):
        """Check if IP is blocked and return response if so. Uses in-memory cache."""
        try:
            from security.ip_blocking import get_ip_blocker

            # B8: Check in-memory cache first
            now_ts = time.time()
            cache_checked, cached_response = self._get_cached_ip_block(client_ip, now_ts)
            if cache_checked:
                return cached_response

            blocker = get_ip_blocker()
            is_blocked, blocked_until = await blocker.is_blocked(client_ip)

            # B8: Store result in cache
            self._ip_block_cache[client_ip] = (
                is_blocked,
                blocked_until,
                now_ts + self._ip_block_cache_ttl,
            )

            if is_blocked:
                return await self._build_blocked_ip_response(
                    request,
                    client_ip,
                    blocked_until,
                )
        except ImportError:
            pass  # IP blocking not available
        except Exception as e:
            logger.debug(f"IP blocking check skipped: {e}")
        return None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        # Skip rate limiting for static files or root
        if path.startswith("/static") or path == "/":
            await self.app(scope, receive, send)
            return

        # VULN-10: In production, only exempt health checks (for load balancers).
        # In development, also exempt docs/openapi for developer convenience.
        exempt_paths = ["/health"]
        try:
            from config import get_settings

            if not get_settings().is_production:
                exempt_paths.extend(["/docs", "/openapi.json", "/redoc"])
        except Exception:
            pass

        if any(path.startswith(p) for p in exempt_paths):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        client_ip = get_client_ip(request)

        # A+ Security: Check if IP is blocked first
        blocked_response = await self._check_ip_block(request, client_ip)
        if blocked_response:
            await blocked_response(scope, receive, send)
            return

        # Get rate limit key and limits for this request
        rate_key = self._get_rate_key(request)
        calls, period = get_rate_limit_for_path(path, self.calls, self.period)

        now = time.time()

        # Periodic cleanup of old entries to prevent memory leak
        self._maybe_cleanup(now)

        rate_limited = False
        remaining = 0
        with self._lock:
            # Get history for this rate key
            history = self.request_history[rate_key]

            # Remove timestamps older than the period
            while history and history[0] < now - period:
                history.popleft()

            # Check if limit exceeded
            if len(history) >= calls:
                rate_limited = True
            else:
                # Add current timestamp
                history.append(now)
                remaining = calls - len(history)

        # Do not await logging, database work, or response I/O while holding
        # the synchronous lock used to protect the in-memory counters.
        if rate_limited:
            await self._send_rate_limit_exceeded(
                scope, receive, send, request, client_ip, path, calls, period
            )
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-RateLimit-Limit", str(calls))
                headers.append("X-RateLimit-Remaining", str(remaining))
                headers.append("X-RateLimit-Reset", str(int(now + period)))
            await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _send_rate_limit_exceeded(
        self,
        scope,
        receive,
        send,
        request: Request,
        client_ip: str,
        path: str,
        calls: int,
        period: int,
    ) -> None:
        logger.warning(
            f"Rate limit exceeded for IP: {client_ip}, path: {path} (limit: {calls}/{period}s)"
        )

        # A+ Security: Record violation for potential blocking
        try:
            from security.ip_blocking import get_ip_blocker

            blocker = get_ip_blocker()
            # Use fire_and_forget to not block the response
            if len(self.background_tasks) < self.MAX_BACKGROUND_TASKS:
                violation_task = asyncio.create_task(
                    blocker.record_violation(client_ip, f"rate_limit:{path}")
                )
                self.background_tasks.add(violation_task)
                violation_task.add_done_callback(self.background_tasks.discard)
        except Exception:
            pass

        # Security-log persistence is sampled, bounded, and detached from the
        # 429 response so rejected traffic cannot consume a DB connection per
        # request or increase response latency.
        if (
            self._should_log_rate_limit_violation(client_ip, path, period, time.time())
            and len(self.background_tasks) < self.MAX_BACKGROUND_TASKS
        ):
            log_task = asyncio.create_task(
                self._log_rate_limit_violation(request, client_ip, path, calls, period)
            )
            self.background_tasks.add(log_task)
            log_task.add_done_callback(self.background_tasks.discard)

        response = JSONResponse(
            status_code=429,
            content={
                "success": False,
                "message": "Too many requests. Please try again later.",
                "code": "RATE_LIMIT_EXCEEDED",
            },
            headers={"Retry-After": str(period)},
        )
        await response(scope, receive, send)

    def _cleanup_request_history(self, now: float, cutoff_time: float) -> None:
        ips_to_remove = []
        for ip, history in self.request_history.items():
            while history and history[0] < now - self.period:
                history.popleft()
            if not history or history[-1] < cutoff_time:
                ips_to_remove.append(ip)

        for ip in ips_to_remove:
            del self.request_history[ip]

        if len(self.request_history) > self.MAX_TRACKED_IPS:
            sorted_ips = sorted(self.request_history.items(), key=lambda x: x[1][-1] if x[1] else 0)
            for ip, _ in sorted_ips[: len(sorted_ips) // 2]:
                del self.request_history[ip]
            logger.warning(
                f"Rate limiter forced cleanup: reduced from "
                f"{len(sorted_ips)} to {len(self.request_history)} IPs"
            )

        if ips_to_remove:
            msg = f"Rate limiter cleanup: removed {len(ips_to_remove)} inactive IPs"
            logger.debug(msg)

    def _cleanup_ip_block_cache(self, now: float) -> None:
        expired_ips = [
            ip for ip, (_, _, expire_at) in self._ip_block_cache.items() if now >= expire_at
        ]
        for ip in expired_ips:
            del self._ip_block_cache[ip]

    def _maybe_cleanup(self, now: float) -> None:
        """Cleanup old entries periodically to prevent memory leak."""
        # Check if cleanup is needed (non-blocking check first)
        if now - self._last_cleanup < self.CLEANUP_INTERVAL:
            return

        with self._lock:
            # Double-check after acquiring lock
            if now - self._last_cleanup < self.CLEANUP_INTERVAL:
                return

            self._last_cleanup = now
            cutoff_time = now - self.period * 2  # Keep entries for 2x period

            self._cleanup_request_history(now, cutoff_time)
            self._cleanup_ip_block_cache(now)
            self._rate_limit_log_cache = {
                key: timestamp
                for key, timestamp in self._rate_limit_log_cache.items()
                if now - timestamp < self.CLEANUP_INTERVAL
            }
