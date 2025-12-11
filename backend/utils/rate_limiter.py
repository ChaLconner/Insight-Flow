from fastapi import Request, HTTPException, status
from services.cache_service import cache_service
import time

class RateLimiter:
    def __init__(self, requests: int = 5, window: int = 60):
        self.requests = requests
        self.window = window
        self.cache_service = cache_service

    async def __call__(self, request: Request):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        
        key = f"rate_limit:{client_ip}:{path}"
        
        # Get current usage
        usage_data = self.cache_service.get(key)
        current_time = time.time()
        
        if usage_data:
            count = usage_data["content"]["count"]
            start_time = usage_data["content"]["start_time"]
            
            # Check if window expired
            if current_time - start_time > self.window:
                # Reset
                self.cache_service.set(key, {"content": {"count": 1, "start_time": current_time}}, timeout=self.window)
            else:
                # Increment
                if count >= self.requests:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests. Please try again later."
                    )
                
                self.cache_service.set(key, {"content": {"count": count + 1, "start_time": start_time}}, timeout=self.window)
        else:
            # First request
            self.cache_service.set(key, {"content": {"count": 1, "start_time": current_time}}, timeout=self.window)

# Common limiters
auth_rate_limiter = RateLimiter(requests=5, window=60)  # 5 requests per minute
