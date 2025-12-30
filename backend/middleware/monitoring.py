import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logger import setup_logger

logger = setup_logger("performance")


class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        process_time = time.time() - start_time
        process_time_ms = round(process_time * 1000, 2)

        # Log slow requests (> 1 second)
        if process_time > 1.0:
            logger.warning(
                f"Slow Request: {request.method} {request.url.path} "
                f"took {process_time_ms}ms - Status: {response.status_code}"
            )

        # Add header for debugging
        response.headers["X-Process-Time"] = str(process_time_ms)

        return response
