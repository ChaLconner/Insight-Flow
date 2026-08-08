"""
Request ID middleware for distributed tracing.
Adds a unique request ID to each request for logging and debugging.
"""

import time
import uuid

from fastapi import Request
from starlette.datastructures import MutableHeaders

from utils.logger import clear_request_context, set_request_context, setup_logger

logger = setup_logger("request_id_middleware")


class RequestIDMiddleware:
    """
    Middleware that adds a unique request ID to each request.
    The request ID is:
    - Generated if not present in incoming X-Request-ID header
    - Added to response headers as X-Request-ID
    - Available in request.state.request_id for logging
    - Set in logging context for structured logs
    """

    HEADER_NAME = "X-Request-ID"

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        header_name_bytes = self.HEADER_NAME.lower().encode("latin1")
        request_id = headers.get(header_name_bytes, b"").decode("latin1")

        if not request_id:
            request_id = str(uuid.uuid4())

        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        path = scope.get("path", "")
        method = scope.get("method", "")

        # Set logging context for structured logs
        set_request_context(
            request_id=request_id,
            path=path,
            method=method,
        )

        # Track request timing
        start_time = time.perf_counter()
        status_code = [500]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 500)
                duration_ms = (time.perf_counter() - start_time) * 1000
                m_headers = MutableHeaders(scope=message)
                m_headers.append(self.HEADER_NAME, request_id)
                m_headers.append("X-Response-Time", f"{duration_ms:.2f}ms")
            await send(message)

        try:
            # Process request
            await self.app(scope, receive, send_wrapper)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log request (skip health checks to reduce noise)
            if not path.startswith("/health"):
                logger.info(f"{method} {path} - {status_code[0]} ({duration_ms:.2f}ms)")
        finally:
            # Always clear context after request
            clear_request_context()


class RequestContextMiddleware:
    """
    Enhanced middleware with request context for structured logging.
    """

    HEADER_NAME = "X-Request-ID"
    CORRELATION_HEADER = "X-Correlation-ID"

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        req_id_bytes = self.HEADER_NAME.lower().encode("latin1")
        corr_id_bytes = self.CORRELATION_HEADER.lower().encode("latin1")

        request_id = headers.get(req_id_bytes, b"").decode("latin1") or str(uuid.uuid4())
        correlation_id = headers.get(corr_id_bytes, b"").decode("latin1") or request_id

        # Store in request state
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id
        scope["state"]["correlation_id"] = correlation_id
        scope["state"]["start_time"] = time.perf_counter()

        # Extract user info if available (after auth)
        scope["state"]["user_id"] = None

        path = scope.get("path", "")
        method = scope.get("method", "")
        status_code = [500]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 500)
                duration_ms = (time.perf_counter() - scope["state"]["start_time"]) * 1000
                m_headers = MutableHeaders(scope=message)
                m_headers.append(self.HEADER_NAME, request_id)
                m_headers.append(self.CORRELATION_HEADER, correlation_id)
                m_headers.append("X-Response-Time", f"{duration_ms:.2f}ms")
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)

            # Calculate duration
            duration_ms = (time.perf_counter() - scope["state"]["start_time"]) * 1000

            # Structured log
            self._log_request(request_id, method, path, status_code[0], duration_ms)

        except Exception as e:
            duration_ms = (time.perf_counter() - scope["state"]["start_time"]) * 1000
            logger.error(f"[{request_id[:8]}] {method} {path} - ERROR: {e!s} ({duration_ms:.2f}ms)")
            raise

    def _log_request(
        self, request_id: str, method: str, path: str, status: int, duration_ms: float
    ):
        """Log request with structured information."""
        # Skip health checks
        if path.startswith("/health"):
            return

        # Skip static files
        if path.startswith("/static"):
            return

        req_id_short = request_id[:8]

        # Determine log level based on status
        if status >= 500:
            log_fn = logger.error
        elif status >= 400:
            log_fn = logger.warning
        else:
            log_fn = logger.info

        log_fn(f"[{req_id_short}] {method} {path} - {status} ({duration_ms:.2f}ms)")


def get_request_id(request: Request) -> str:
    """Helper to get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def get_correlation_id(request: Request) -> str:
    """Helper to get correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")
