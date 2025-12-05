"""
Cache middleware for API responses.
"""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import setup_logger
from services.cache_service import cache_service

logger = setup_logger("cache_middleware")

class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware that uses the singleton CacheService.
    """
    
    def __init__(self, app, cache_timeout: int = 60):
        super().__init__(app)
        self.cache_timeout = cache_timeout
        self.cache_service = cache_service
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate cache key based on URL and method
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)

        cache_key = f"{request.method}:{request.url}"
        
        # Check cache
        cached_data = self.cache_service.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for {cache_key}")
            response = Response(
                content=cached_data["content"],
                status_code=cached_data["status_code"],
                headers=cached_data["headers"]
            )
            response.headers["X-Cache"] = "HIT"
            return response
        
        logger.debug(f"Cache miss for {cache_key}")
        
        # Process request
        response = await call_next(request)
        
        # Cache successful JSON responses
        if (
            200 <= response.status_code < 300 and
            "application/json" in response.headers.get("content-type", "")
        ):
            try:
                # Extract content
                content = None
                if hasattr(response, 'body') and not callable(getattr(response, 'body', None)):
                    content = response.body
                elif hasattr(response, 'content'):
                    content = response.content
                
                if content:
                    self.cache_service.set(cache_key, {
                        "content": content,
                        "status_code": response.status_code,
                        "headers": dict(response.headers)
                    }, timeout=self.cache_timeout)
                    
                    response.headers["X-Cache"] = "MISS"
            except Exception as e:
                logger.error(f"Failed to cache response: {e}")
                
        return response