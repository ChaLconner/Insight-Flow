import os

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security Headers - Standard protection
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content-Security-Policy for API
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        # Permissions-Policy - restrict browser features for API
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Cross-Origin headers
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # HSTS (Strict-Transport-Security) - Enable in production
        # Only set when running in production/HTTPS environment
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
