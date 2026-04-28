"""
CSRF Protection Middleware for FastAPI.
Implements double-submit cookie pattern for CSRF protection.
"""

import hmac
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from utils.logger import setup_logger

logger = setup_logger("csrf_middleware")

# Configuration
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_TOKEN_LENGTH = 32
CSRF_COOKIE_MAX_AGE = 3600 * 24  # 24 hours
CSRF_SECRET_KEY_ENV = "CSRF_SECRET_KEY"

# Safe methods that don't require CSRF validation
SAFE_METHODS: set[str] = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Paths that are exempt from CSRF validation
CSRF_EXEMPT_PATHS: set[str] = {
    "/auth/login",
    "/auth/register",
    "/auth/google",
    "/auth/github",
    "/auth/refresh",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/validate-reset-token",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/google",
    "/api/v1/auth/github",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/validate-reset-token",
    "/health",
    "/health/db",
    "/health/cache",
    "/health/full",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}

CSRF_EXEMPT_PREFIXES: set[str] = set()


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def validate_csrf_token(cookie_token: str | None, header_token: str | None) -> bool:
    """
    Validate CSRF token using constant-time comparison.
    Both tokens must exist and match.
    """
    if not cookie_token or not header_token:
        return False

    return hmac.compare_digest(cookie_token, header_token)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection using double-submit cookie pattern.

    How it works:
    1. On first request, a CSRF token is generated and set as a cookie
    2. For state-changing requests (POST, PUT, DELETE, PATCH):
       - Client must include the token in X-CSRF-Token header
       - Server compares header token with cookie token
    3. If tokens don't match, request is rejected with 403
    """

    def __init__(
        self,
        app,
        cookie_name: str = CSRF_COOKIE_NAME,
        header_name: str = CSRF_HEADER_NAME,
        cookie_secure: bool = True,
        cookie_httponly: bool = False,  # Must be False so JS can read it
        cookie_samesite: str = "lax",
        exempt_paths: set[str] | None = None,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite
        self.exempt_paths = exempt_paths or CSRF_EXEMPT_PATHS
        self.enabled = enabled

    def is_exempt(self, request: Request) -> bool:
        """Check if the request path is exempt from CSRF validation."""
        path = request.url.path.rstrip("/")

        # Check exact match
        if path in self.exempt_paths:
            return True

        # Prefix exemptions must be explicit; auth endpoints are exact-match only.
        return any(path.startswith(exempt_prefix) for exempt_prefix in CSRF_EXEMPT_PREFIXES)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip CSRF validation if disabled
        if not self.enabled:
            return await call_next(request)  # type: ignore

        # Skip for safe methods
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            # Ensure CSRF cookie is set for subsequent requests
            if not request.cookies.get(self.cookie_name):
                csrf_token = generate_csrf_token()
                response.set_cookie(
                    key=self.cookie_name,
                    value=csrf_token,
                    max_age=CSRF_COOKIE_MAX_AGE,
                    secure=self.cookie_secure,
                    httponly=self.cookie_httponly,
                    samesite=self.cookie_samesite,
                    path="/",
                )
            return response  # type: ignore

        # Skip for exempt paths
        if self.is_exempt(request):
            response = await call_next(request)
            return response  # type: ignore

        # Validate CSRF token for state-changing methods
        cookie_token = request.cookies.get(self.cookie_name)
        header_token = request.headers.get(self.header_name)

        if not validate_csrf_token(cookie_token, header_token):
            logger.warning(
                f"CSRF validation failed for {request.method} {request.url.path} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "CSRF token validation failed",
                    "code": "CSRF_VALIDATION_FAILED",
                },
            )

        response = await call_next(request)
        return response  # type: ignore


def get_csrf_token_endpoint():
    """
    Utility function to create a CSRF token endpoint.
    Add this to your router if you need an explicit endpoint to get CSRF token.
    """
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/csrf-token", tags=["security"])
    async def get_csrf_token(request: Request):
        """
        Get a new CSRF token.
        The token is also set as a cookie in the response.
        """
        token = request.cookies.get(CSRF_COOKIE_NAME)
        if not token:
            token = generate_csrf_token()

        return {"csrf_token": token}

    return router
