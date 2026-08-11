"""
Response Cache Headers Middleware
Adds appropriate Cache-Control headers based on endpoint type.
"""

import re
from typing import ClassVar

from starlette.datastructures import MutableHeaders

CACHE_CONTROL_PRIVATE_60 = "private, max-age=60, stale-while-revalidate=120"


class ResponseCacheMiddleware:
    """
    Middleware to add Cache-Control headers to API responses.

    - Static/health endpoints: Long cache
    - Analytics/dashboard: Short cache (client-side only)
    - Mutable endpoints (POST, PUT, DELETE): No cache
    """

    # Patterns for endpoints that can be cached
    CACHEABLE_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        # Health endpoints - can be cached for 30 seconds
        (re.compile(r"^/health"), "public, max-age=30"),
        # Metrics - short cache
        (re.compile(r"^/metrics"), "public, max-age=15"),
        # Analytics overview - client-side cache with stale-while-revalidate for instant loads
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

        if any(pattern.match(path) for pattern in self.NO_CACHE_PATTERNS):
            return "no-store, no-cache, must-revalidate"

        for pattern, cache_control in self.CACHEABLE_PATTERNS:
            if pattern.match(path):
                return cache_control

        if "Cache-Control" not in headers:
            return "private, no-cache"
        return None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                cache_control = self._get_cache_control(method, path, headers)
                if cache_control:
                    headers["Cache-Control"] = cache_control

            await send(message)

        await self.app(scope, receive, send_wrapper)
