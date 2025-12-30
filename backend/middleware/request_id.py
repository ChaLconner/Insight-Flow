"""
Request ID middleware for distributed tracing.
Adds a unique request ID to each request for logging and debugging.
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logger import clear_request_context, set_request_context, setup_logger

logger = setup_logger("request_id_middleware")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.
    The request ID is:
    - Generated if not present in incoming X-Request-ID header
    - Added to response headers as X-Request-ID
    - Available in request.state.request_id for logging
    - Set in logging context for structured logs
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate request ID
        request_id = request.headers.get(self.HEADER_NAME)
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for access in routes
        request.state.request_id = request_id

        # Set logging context for structured logs
        set_request_context(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        # Track request timing
        start_time = time.perf_counter()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Add headers to response
            response.headers[self.HEADER_NAME] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            # Log request (skip health checks to reduce noise)
            if not request.url.path.startswith("/health"):
                logger.info(
                    f"{request.method} {request.url.path} - "
                    f"{response.status_code} ({duration_ms:.2f}ms)"
                )

            return response  # type: ignore
        finally:
            # Always clear context after request
            clear_request_context()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware with request context for structured logging.
    """

    HEADER_NAME = "X-Request-ID"
    CORRELATION_HEADER = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate IDs
        request_id = request.headers.get(self.HEADER_NAME, str(uuid.uuid4()))
        correlation_id = request.headers.get(self.CORRELATION_HEADER, request_id)

        # Store in request state
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.start_time = time.perf_counter()

        # Extract user info if available (after auth)
        request.state.user_id = None

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - request.state.start_time) * 1000

            # Add headers
            response.headers[self.HEADER_NAME] = request_id
            response.headers[self.CORRELATION_HEADER] = correlation_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            # Structured log
            self._log_request(request, response, duration_ms)

            return response  # type: ignore

        except Exception as e:
            duration_ms = (time.perf_counter() - request.state.start_time) * 1000
            logger.error(
                f"[{request_id[:8]}] {request.method} {request.url.path} - "
                f"ERROR: {e!s} ({duration_ms:.2f}ms)"
            )
            raise

    def _log_request(self, request: Request, response: Response, duration_ms: float):
        """Log request with structured information."""
        # Skip health checks
        if request.url.path.startswith("/health"):
            return

        # Skip static files
        if request.url.path.startswith("/static"):
            return

        request_id = request.state.request_id[:8]

        # Determine log level based on status
        status = response.status_code
        if status >= 500:
            log_fn = logger.error
        elif status >= 400:
            log_fn = logger.warning
        else:
            log_fn = logger.info

        log_fn(
            f"[{request_id}] {request.method} {request.url.path} - {status} ({duration_ms:.2f}ms)"
        )


def get_request_id(request: Request) -> str:
    """Helper to get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def get_correlation_id(request: Request) -> str:
    """Helper to get correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")
