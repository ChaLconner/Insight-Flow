"""
Response Cache Headers Middleware
Adds appropriate Cache-Control headers based on endpoint type.
"""

import re
from hashlib import sha256
from typing import ClassVar

from starlette.datastructures import Headers, MutableHeaders

CACHE_CONTROL_PRIVATE_60 = "private, max-age=60, stale-while-revalidate=120"
CACHE_CONTROL_NO_STORE = "no-store, no-cache, must-revalidate"


class ResponseCacheMiddleware:
    """
    Middleware to add Cache-Control headers to API responses.

    - Public health/metrics endpoints: short cache with validators
    - Analytics/dashboard: private client-side cache policy is disabled
    - Mutable endpoints (POST, PUT, DELETE): No cache
    """

    # Patterns for endpoints that can be cached
    CACHEABLE_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        # Health endpoints - can be cached for 30 seconds
        (re.compile(r"^/health"), "public, max-age=30"),
        # Metrics - short cache
        (re.compile(r"^/metrics"), "public, max-age=15"),
        # Analytics overview remains documented for compatibility, but the
        # authenticated-path rule below forces no-store.
        (
            re.compile(r"^/(?:api/v1/)?analytics/overview"),
            CACHE_CONTROL_PRIVATE_60,
        ),
        # Dashboard endpoints - client-side cache with stale-while-revalidate
        (
            re.compile(r"^/(?:api/v1/)?dashboard/overview"),
            CACHE_CONTROL_PRIVATE_60,
        ),
        (
            re.compile(r"^/(?:api/v1/)?dashboard/today-tasks"),
            "private, max-age=30, stale-while-revalidate=60",
        ),
        (
            re.compile(r"^/(?:api/v1/)?dashboard/recent-projects"),
            CACHE_CONTROL_PRIVATE_60,
        ),
        (
            re.compile(r"^/(?:api/v1/)?dashboard/team-activity"),
            "private, max-age=30, stale-while-revalidate=60",
        ),
        # Projects list - short cache for navigation
        (
            re.compile(r"^/(?:api/v1/)?projects/?$"),
            "private, max-age=15, stale-while-revalidate=30",
        ),
        # User profile (rarely changes) - client-side cache
        (
            re.compile(r"^/(?:api/v1/)?users/me$"),
            "private, max-age=300, stale-while-revalidate=600",
        ),
    ]

    # Only public, non-user-scoped representations are eligible for validators.
    # Account-scoped responses intentionally remain no-store to prevent browser
    # cache reuse across logout or account switching.
    PUBLIC_VALIDATOR_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        # Only liveness/readiness are safe for shared caches. Detailed health
        # responses can contain dependency topology and pool information.
        re.compile(r"^/health(?:/ready)?$"),
        re.compile(r"^/metrics$"),
    ]

    PRIVATE_HEALTH_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^/health/(?:db|cache|full)$"),
    ]

    # These routes return account- or project-scoped data. Browser caching can
    # survive logout/account switching, so these responses must never be
    # reused by a subsequent request.
    AUTHENTICATED_PATH_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^/(?:api/v1/)?analytics/overview"),
        re.compile(r"^/(?:api/v1/)?dashboard/overview"),
        re.compile(r"^/(?:api/v1/)?dashboard/today-tasks"),
        re.compile(r"^/(?:api/v1/)?dashboard/recent-projects"),
        re.compile(r"^/(?:api/v1/)?dashboard/team-activity"),
        re.compile(r"^/(?:api/v1/)?projects/?$"),
        re.compile(r"^/(?:api/v1/)?users/me$"),
    ]

    # Endpoints that should never be cached
    NO_CACHE_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^/(?:api/v1/)?auth/"),
        re.compile(r"^/(?:api/v1/)?tasks/"),  # Tasks change frequently
        re.compile(r"^/(?:api/v1/)?projects/[^/]+/tasks"),  # Project tasks
        re.compile(r"^/(?:api/v1/)?notifications/"),
    ]

    def __init__(self, app):
        self.app = app

    def _get_cache_control(self, method: str, path: str, headers: MutableHeaders) -> str | None:
        if method != "GET":
            return "no-store, no-cache, must-revalidate"

        no_store_patterns = (
            *self.NO_CACHE_PATTERNS,
            *self.AUTHENTICATED_PATH_PATTERNS,
            *self.PRIVATE_HEALTH_PATTERNS,
        )
        if any(pattern.match(path) for pattern in no_store_patterns):
            return CACHE_CONTROL_NO_STORE

        for pattern, cache_control in self.CACHEABLE_PATTERNS:
            if pattern.match(path):
                return cache_control

        if "Cache-Control" not in headers:
            return "private, no-cache"
        return None

    def _is_public_validator_path(self, path: str) -> bool:
        return any(pattern.match(path) for pattern in self.PUBLIC_VALIDATOR_PATTERNS)

    @staticmethod
    def _matches_if_none_match(if_none_match: str | None, etag: str) -> bool:
        if not if_none_match:
            return False

        normalized_etag = etag.removeprefix("W/")
        for candidate in if_none_match.split(","):
            candidate = candidate.strip()
            if candidate == "*" or candidate.removeprefix("W/") == normalized_etag:
                return True
        return False

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        if_none_match = Headers(scope=scope).get("if-none-match")
        buffered_start = None
        buffered_body: list[bytes] = []
        should_buffer = False

        async def send_wrapper(message):
            nonlocal buffered_start, should_buffer

            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                cache_control = self._get_cache_control(method, path, headers)
                if cache_control:
                    headers["Cache-Control"] = cache_control

                should_buffer = (
                    method == "GET"
                    and self._is_public_validator_path(path)
                    and message.get("status") == 200
                    and cache_control is not None
                    and cache_control.startswith("public")
                    and "ETag" not in headers
                )
                if should_buffer:
                    buffered_start = message
                    return

            if should_buffer and message["type"] == "http.response.body":
                buffered_body.append(message.get("body", b""))
                if message.get("more_body", False):
                    return

                if buffered_start is None:
                    await send(message)
                    return

                body = b"".join(buffered_body)
                # A weak validator is correct even when an outer compression
                # middleware selects a different wire representation.
                etag = f'W/"{sha256(body).hexdigest()}"'
                response_headers = MutableHeaders(scope=buffered_start)
                response_headers["ETag"] = etag

                if self._matches_if_none_match(if_none_match, etag):
                    buffered_start["status"] = 304
                    response_headers["Content-Length"] = "0"
                    if "Content-Type" in response_headers:
                        del response_headers["Content-Type"]
                    await send(buffered_start)
                    await send({"type": "http.response.body", "body": b"", "more_body": False})
                    return

                await send(buffered_start)
                await send({"type": "http.response.body", "body": body, "more_body": False})
                return

            await send(message)

        await self.app(scope, receive, send_wrapper)
