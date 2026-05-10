"""
Response Cache Headers Middleware
Adds appropriate Cache-Control headers based on endpoint type.
"""

import re
from typing import ClassVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class ResponseCacheMiddleware(BaseHTTPMiddleware):
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

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Skip for non-GET requests (mutations should never be cached)
        if request.method != "GET":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            return response

        path = request.url.path

        # Check if path matches no-cache patterns
        for pattern in self.NO_CACHE_PATTERNS:
            if pattern.match(path):
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
                return response

        # Check if path matches cacheable patterns
        for pattern, cache_control in self.CACHEABLE_PATTERNS:
            if pattern.match(path):
                response.headers["Cache-Control"] = cache_control
                return response

        # Default: private, no-cache (revalidate with server)
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "private, no-cache"

        return response
