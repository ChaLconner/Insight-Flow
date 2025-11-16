"""
Cache middleware for API responses.
"""
import time
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import setup_logger

logger = setup_logger("cache_middleware")

class CacheMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory cache middleware for API responses.
    """
    
    def __init__(self, app, cache_timeout: int = 300):
        super().__init__(app)
        self.cache_timeout = cache_timeout  # Cache timeout in seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate cache key based on URL and method
        cache_key = f"{request.method}:{request.url}"
        
        # Check if response is cached and not expired
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            current_time = time.time()
            
            # Check if cache is still valid
            if current_time - cached_data["timestamp"] < self.cache_timeout:
                logger.debug(f"Cache hit for {cache_key}")
                
                # Return cached response
                response = Response(
                    content=cached_data["content"],
                    status_code=cached_data["status_code"],
                    headers=cached_data["headers"]
                )
                
                # Add cache header
                response.headers["X-Cache"] = "HIT"
                return response
        
        logger.debug(f"Cache miss for {cache_key}")
        
        # Process request and get response
        response = await call_next(request)
        
        # Only cache GET requests with successful status codes
        if (
            request.method == "GET" and
            200 <= response.status_code < 300 and
            "application/json" in response.headers.get("content-type", "")
        ):
            # Log response type for debugging
            logger.debug(f"Response type: {type(response)}")
            
            # Try to get content from response - handle different response types
            try:
                # Check for body attribute first (but not if it's a method)
                if hasattr(response, 'body') and not callable(getattr(response, 'body', None)):
                    content = response.body
                # Check for content attribute
                elif hasattr(response, 'content'):
                    content = response.content
                else:
                    # Skip caching for unknown response types (including streaming responses)
                    logger.debug("Skipping cache for unknown response type")
                    return response
                    
                logger.debug(f"Successfully extracted content for caching")
                
                # Cache the response
                self.cache[cache_key] = {
                    "content": content,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "timestamp": time.time()
                }
            except AttributeError as e:
                # Handle AttributeError specifically for streaming responses
                if "'_StreamingResponse' object has no attribute 'body'" in str(e):
                    logger.debug("Skipping cache for streaming response")
                else:
                    logger.error(f"AttributeError accessing response: {e}")
                return response
            except Exception as e:
                logger.error(f"Failed to extract content from response: {e}")
                logger.error(f"Response type: {type(response)}")
                # Don't cache if we can't extract content, just return the response
                return response
            
            # Add cache header
            response.headers["X-Cache"] = "MISS"
            logger.debug(f"Cached response for {cache_key}")
        
        return response
    
    def clear_cache(self):
        """Clear the entire cache."""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def clear_cache_for_pattern(self, pattern: str):
        """Clear cache entries matching a pattern."""
        keys_to_remove = [key for key in self.cache.keys() if pattern in key]
        for key in keys_to_remove:
            del self.cache[key]
        logger.info(f"Cleared {len(keys_to_remove)} cache entries matching pattern: {pattern}")