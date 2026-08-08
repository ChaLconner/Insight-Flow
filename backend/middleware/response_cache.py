"""
Response Cache Headers Middleware
Adds appropriate Cache-Control headers based on endpoint type.
"""

import re
from typing import ClassVar

from starlette.datastructures import MutableHeaders


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
            "private, max-age=60, stale-while-revalidate=120",
        ),
        # Dashboard endpoints - client-side cache with stale-while-revalidate
        (
            re.compile(r"^/(?:api/v1/)?dashboard/overview"),
            "private, max-age=60, stale-while-revalidate=120",
        ),
        (
            re.compile(r"^/(?:api/v1/)?dashboard/today-tasks"),
            "private, max-age=30, stale-while-revalidate=60",
        ),
        (
            re.compile(r"^/(?:api/v1/)?dashboard/recent-projects"),
            "private, max-age=60, stale-while-revalidate=120",
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

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)

                cache_control = None

                # Skip for non-GET requests (mutations should never be cached)
                if method != "GET":
                    cache_control = "no-store, no-cache, must-revalidate"
                else:
                    # Check if path matches no-cache patterns
                    for pattern in self.NO_CACHE_PATTERNS:
                        if pattern.match(path):
                            cache_control = "no-store, no-cache, must-revalidate"
                            break

                    if not cache_control:
                        # Check if path matches cacheable patterns
                        for pattern, c_control in self.CACHEABLE_PATTERNS:
                            if pattern.match(path):
                                cache_control = c_control
                                break

                    # Default: private, no-cache (revalidate with server)
                    if not cache_control and "Cache-Control" not in headers:
                        cache_control = "private, no-cache"

                if cache_control:
                    headers["Cache-Control"] = cache_control

            await send(message)

        await self.app(scope, receive, send_wrapper)
