import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from collections import defaultdict, deque
import logging

logger = logging.getLogger("rate_limit")

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        # Dictionary to store request timestamps per IP
        # Value is a deque of timestamps
        self.request_history = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for static files or health checks
        if request.url.path.startswith("/static") or request.url.path == "/":
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
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
                    "code": "RATE_LIMIT_EXCEEDED"
                },
                headers={"Retry-After": str(self.period)}
            )
            
        # Add current timestamp
        history.append(now)
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(self.calls - len(history))
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))
        
        return response
