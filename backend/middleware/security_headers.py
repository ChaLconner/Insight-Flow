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
        from config import get_settings

        settings = get_settings()

        csp_policy = "default-src 'none'; frame-ancestors 'none'"

        # Add reporting if configured (or default to our own endpoint)
        report_uri = settings.security_report_uri or "/api/v1/security/csp-report"
        csp_policy += f"; report-uri {report_uri}; report-to csp-endpoint"

        response.headers["Content-Security-Policy"] = csp_policy
        report_to_header = (
            f'{{"group":"csp-endpoint","max_age":10886400,"endpoints":[{{"url":"{report_uri}"}}]}}'
        )
        response.headers["Report-To"] = report_to_header

        # Permissions-Policy - restrict browser features for API
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Cross-Origin headers
        # Use unsafe-none to allow OAuth popups to work correctly without COOP isolation issues
        response.headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # HSTS (Strict-Transport-Security) - Enable in production
        # Only set when running in production/HTTPS environment
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
