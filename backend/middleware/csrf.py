"""
CSRF Protection Middleware for FastAPI.
Implements double-submit cookie pattern for CSRF protection.
"""

import hmac
import secrets

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import JSONResponse

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
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/validate-reset-token",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/google",
    "/api/v1/auth/github",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/validate-reset-token",
    # Stripe authenticates webhooks with the Stripe-Signature header. Browser
    # double-submit CSRF cannot be supplied by Stripe and must not gate this
    # exact endpoint; signature verification remains mandatory in the router.
    "/api/v1/payment/webhook",
    # CSP reports are browser-generated telemetry and cannot carry the
    # application's custom CSRF header. Body/schema/rate limits protect this
    # unauthenticated endpoint from becoming an ingestion sink.
    "/api/v1/security/csp-report",
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
CSRF_BEARER_ONLY_PATHS: set[str] = {"/auth/refresh", "/api/v1/auth/refresh"}


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


class CSRFMiddleware:
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
        self.app = app
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

        # A caller that supplies a refresh token in an Authorization header
        # is not relying on ambient browser cookies and is therefore not
        # exposed to cross-site cookie submission. Cookie-based refreshes
        # still require the double-submit token.
        if (
            path in CSRF_BEARER_ONLY_PATHS
            and request.headers.get("authorization", "").startswith("Bearer ")
            and not request.cookies.get("refresh_token")
        ):
            return True

        # Prefix exemptions must be explicit; auth endpoints are exact-match only.
        return any(path.startswith(exempt_prefix) for exempt_prefix in CSRF_EXEMPT_PREFIXES)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip CSRF validation if disabled
        if not self.enabled:
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        # Skip for safe methods
        if request.method in SAFE_METHODS:
            # Ensure CSRF cookie is set for subsequent requests
            if not request.cookies.get(self.cookie_name):
                csrf_token = generate_csrf_token()

                async def send_wrapper(message):
                    if message["type"] == "http.response.start":
                        headers = MutableHeaders(scope=message)
                        cookie_val = f"{self.cookie_name}={csrf_token}; Max-Age={CSRF_COOKIE_MAX_AGE}; Path=/; SameSite={self.cookie_samesite}"
                        if self.cookie_secure:
                            cookie_val += "; Secure"
                        if self.cookie_httponly:
                            cookie_val += "; HttpOnly"
                        headers.append("set-cookie", cookie_val)
                    await send(message)

                await self.app(scope, receive, send_wrapper)
            else:
                await self.app(scope, receive, send)
            return

        # Skip for exempt paths
        if self.is_exempt(request):
            await self.app(scope, receive, send)
            return

        # Validate CSRF token for state-changing methods
        cookie_token = request.cookies.get(self.cookie_name)
        header_token = request.headers.get(self.header_name)

        if not validate_csrf_token(cookie_token, header_token):
            client_host = request.client.host if request.client else "unknown"
            logger.warning(
                f"CSRF validation failed for {request.method} {request.url.path} from {client_host}"
            )
            response = JSONResponse(
                status_code=403,
                content={
                    "detail": "CSRF token validation failed",
                    "code": "CSRF_VALIDATION_FAILED",
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


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
