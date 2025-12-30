import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    # Maximum number of IPs to track before forcing cleanup
    MAX_TRACKED_IPS = 10000
    # Cleanup interval in seconds
    CLEANUP_INTERVAL = 300  # 5 minutes

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        # Dictionary to store request timestamps per IP
        # Value is a deque of timestamps
        self.request_history: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for static files or health checks
        if request.url.path.startswith("/static") or request.url.path == "/":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Periodic cleanup of old entries to prevent memory leak
        self._maybe_cleanup(now)

        with self._lock:
            # Get history for this IP
            history = self.request_history[client_ip]

            # Remove timestamps older than the period
            while history and history[0] < now - self.period:
                history.popleft()

            # Check if limit exceeded
            if len(history) >= self.calls:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "message": "Too many requests. Please try again later.",
                        "code": "RATE_LIMIT_EXCEEDED",
                    },
                    headers={"Retry-After": str(self.period)},
                )

            # Add current timestamp
            history.append(now)
            remaining = self.calls - len(history)

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))

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
                    f"Rate limiter forced cleanup: reduced from {len(sorted_ips)} to {len(self.request_history)} IPs"
                )

            if ips_to_remove:
                logger.debug(f"Rate limiter cleanup: removed {len(ips_to_remove)} inactive IPs")
