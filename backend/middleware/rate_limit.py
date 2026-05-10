"""
In-memory rate limiting middleware for FastAPI (fallback when Redis is unavailable).

Used by ``core/middleware_config.py`` as the fallback global rate limiter.
For fine-grained per-route limits, see ``rate_limiter.py`` (SlowAPI-based).
"""

import logging
import threading
import time
from collections import defaultdict, deque
from typing import TYPE_CHECKING

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from database import AsyncSessionLocal
from services.security_log_service import SecurityLogService

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


class RateLimitMiddleware(BaseHTTPMiddleware):
    # Maximum number of IPs to track before forcing cleanup
    MAX_TRACKED_IPS = 10000
    # Cleanup interval in seconds
    CLEANUP_INTERVAL = 300  # 5 minutes

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
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

    def _get_rate_key(self, request: Request) -> str:
        """Get rate limiting key for the request."""
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Check if this path has a specific rate limit
        for prefix in RATE_LIMIT_CONFIG:
            if path.startswith(prefix):
                return f"{client_ip}:{prefix}"

        # Default: use IP only for general rate limiting
        return f"{client_ip}:default"

    async def _check_ip_block(self, request: Request, client_ip: str):
        """Check if IP is blocked and return response if so. Uses in-memory cache."""
        try:
            from security.ip_blocking import get_ip_blocker

            # B8: Check in-memory cache first
            now_ts = time.time()
            cached = self._ip_block_cache.get(client_ip)
            if cached:
                is_blocked_cached, blocked_until_cached, expire_at = cached
                if now_ts < expire_at:
                    # Cache hit — use cached result
                    if not is_blocked_cached:
                        return None  # Not blocked, skip DB
                    # Blocked — build response from cache
                    remaining = 0
                    if blocked_until_cached:
                        now_dt = __import__("datetime").datetime.now(__import__("datetime").UTC)
                        remaining = int((blocked_until_cached - now_dt).total_seconds())
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
                else:
                    # Cache expired — remove stale entry
                    del self._ip_block_cache[client_ip]

            blocker = get_ip_blocker()
            is_blocked, blocked_until = await blocker.is_blocked(client_ip)

            # B8: Store result in cache
            self._ip_block_cache[client_ip] = (
                is_blocked,
                blocked_until,
                now_ts + self._ip_block_cache_ttl,
            )

            if is_blocked:
                remaining = 0
                if blocked_until:
                    # Calculate remaining time securely
                    now = __import__("datetime").datetime.now(__import__("datetime").UTC)
                    remaining = int((blocked_until - now).total_seconds())

                logger.warning(f"Blocked IP {client_ip} attempted access")

                # Log blocked access attempt
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
                    logger.error(f"Failed to log blocked access: {e}")

                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "message": ("Access temporarily blocked due to suspicious activity."),
                        "code": "IP_BLOCKED",
                        "retry_after": remaining,
                    },
                    headers={"Retry-After": str(remaining)},
                )
        except ImportError:
            pass  # IP blocking not available
        except Exception as e:
            logger.debug(f"IP blocking check skipped: {e}")
        return None

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip rate limiting for static files or root
        if path.startswith("/static") or path == "/":
            return await call_next(request)

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
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        # A+ Security: Check if IP is blocked first
        blocked_response = await self._check_ip_block(request, client_ip)
        if blocked_response:
            return blocked_response

        # Get rate limit key and limits for this request
        rate_key = self._get_rate_key(request)
        path = request.url.path
        calls, period = get_rate_limit_for_path(path, self.calls, self.period)

        now = time.time()

        # Periodic cleanup of old entries to prevent memory leak
        self._maybe_cleanup(now)

        with self._lock:
            # Get history for this rate key
            history = self.request_history[rate_key]

            # Remove timestamps older than the period
            while history and history[0] < now - period:
                history.popleft()

            # Check if limit exceeded
            if len(history) >= calls:
                logger.warning(
                    f"Rate limit exceeded for IP: {client_ip}, path: {path} "
                    f"(limit: {calls}/{period}s)"
                )

                # A+ Security: Record violation for potential blocking
                try:
                    from security.ip_blocking import get_ip_blocker

                    blocker = get_ip_blocker()
                    # Use fire_and_forget to not block the response
                    import asyncio

                    task = asyncio.create_task(
                        blocker.record_violation(client_ip, f"rate_limit:{path}")
                    )
                    self.background_tasks.add(task)
                    task.add_done_callback(self.background_tasks.discard)
                except Exception:
                    pass

                # Log rate limit violation
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
                    logger.error(f"Failed to log rate limit: {e}")

                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "message": ("Too many requests. Please try again later."),
                        "code": "RATE_LIMIT_EXCEEDED",
                    },
                    headers={"Retry-After": str(period)},
                )

            # Add current timestamp
            history.append(now)
            remaining = calls - len(history)

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + period))

        return response

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

            # Remove IPs with no recent activity
            ips_to_remove = []
            for ip, history in self.request_history.items():
                # Remove old timestamps
                while history and history[0] < now - self.period:
                    history.popleft()
                # Mark empty histories for removal
                if not history or history[-1] < cutoff_time:
                    ips_to_remove.append(ip)

            for ip in ips_to_remove:
                del self.request_history[ip]

            # Force cleanup if too many IPs tracked
            if len(self.request_history) > self.MAX_TRACKED_IPS:
                # Sort by last activity and remove oldest half
                sorted_ips = sorted(
                    self.request_history.items(), key=lambda x: x[1][-1] if x[1] else 0
                )
                for ip, _ in sorted_ips[: len(sorted_ips) // 2]:
                    del self.request_history[ip]
                logger.warning(
                    f"Rate limiter forced cleanup: reduced from "
                    f"{len(sorted_ips)} to {len(self.request_history)} IPs"
                )

            if ips_to_remove:
                msg = f"Rate limiter cleanup: removed {len(ips_to_remove)} inactive IPs"
                logger.debug(msg)

            # B8: Clean up expired IP block cache entries
            expired_ips = [
                ip for ip, (_, _, expire_at) in self._ip_block_cache.items() if now >= expire_at
            ]
            for ip in expired_ips:
                del self._ip_block_cache[ip]
