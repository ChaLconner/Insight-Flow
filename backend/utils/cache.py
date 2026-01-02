"""
Simple in-memory cache utility for dashboard data.
For production, consider using Redis or similar caching solution.
"""

import hashlib
import json
from datetime import datetime, timedelta
from threading import Lock
from typing import Any


class SimpleCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, default_ttl_seconds: int = 60):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._lock = Lock()
        self._default_ttl = timedelta(seconds=default_ttl_seconds)

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix and arguments."""
        key_data = {
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in sorted(kwargs.items())},
        }
        key_hash = hashlib.md5(json.dumps(key_data).encode()).hexdigest()[:12]
        return f"{prefix}:{key_hash}"

    def get(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        with self._lock:
            if key not in self._cache:
                return None

            value, expires_at = self._cache[key]

            if datetime.now() > expires_at:
                # Expired, remove from cache
                del self._cache[key]
                return None

            return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self._default_ttl
        expires_at = datetime.now() + ttl

        with self._lock:
            self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear_prefix(self, prefix: str) -> int:
        """Clear all keys with given prefix."""
        count = 0
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
        return count

    def clear_all(self) -> int:
        """Clear entire cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        count = 0
        now = datetime.now()
        with self._lock:
            expired_keys = [k for k, (_, expires_at) in self._cache.items() if now > expires_at]
            for key in expired_keys:
                del self._cache[key]
                count += 1
        return count


# Global cache instance for dashboard data (60 seconds TTL by default)
dashboard_cache = SimpleCache(default_ttl_seconds=60)


def cache_dashboard_stats(ttl_seconds: int = 60):
    """
    Decorator to cache dashboard stats for a user.

    Usage:
        @cache_dashboard_stats(ttl_seconds=120)
        def get_overview_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
            ...
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(self, user_id, *args, **kwargs):
            cache_key = dashboard_cache._make_key(
                f"dashboard_stats:{str(user_id)[:8]}", *args, **kwargs
            )

            # Try to get from cache
            cached = dashboard_cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute function and cache result
            result = func(self, user_id, *args, **kwargs)
            dashboard_cache.set(cache_key, result, ttl_seconds)

            return result

        return wrapper

    return decorator


def invalidate_user_dashboard_cache(user_id: str) -> int:
    """Invalidate all dashboard cache for a specific user."""
    prefix = f"dashboard_stats:{str(user_id)[:8]}"
    return dashboard_cache.clear_prefix(prefix)


# ==============================================================================
# PROJECT CACHE (for project details and lists)
# ==============================================================================

# Global cache instance for project data (30 seconds TTL for faster updates)
project_cache = SimpleCache(default_ttl_seconds=30)


def cache_project_details(ttl_seconds: int = 30):
    """
    Decorator to cache project details.
    Works with async functions.

    Usage:
        @cache_project_details(ttl_seconds=30)
        async def get_project_with_details(self, project_id: uuid.UUID) -> Dict[str, Any]:
            ...
    """

    def decorator(func):
        import asyncio
        import functools

        @functools.wraps(func)
        async def async_wrapper(self, project_id, *args, **kwargs):
            cache_key = project_cache._make_key(f"project:{str(project_id)[:8]}", *args, **kwargs)

            # Try to get from cache
            cached = project_cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute async function and cache result
            result = await func(self, project_id, *args, **kwargs)
            if result is not None:
                project_cache.set(cache_key, result, ttl_seconds)

            return result

        @functools.wraps(func)
        def sync_wrapper(self, project_id, *args, **kwargs):
            cache_key = project_cache._make_key(f"project:{str(project_id)[:8]}", *args, **kwargs)

            # Try to get from cache
            cached = project_cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute function and cache result
            result = func(self, project_id, *args, **kwargs)
            if result is not None:
                project_cache.set(cache_key, result, ttl_seconds)

            return result

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_project_cache(project_id: str) -> int:
    """Invalidate cache for a specific project."""
    prefix = f"project:{str(project_id)[:8]}"
    return project_cache.clear_prefix(prefix)


def invalidate_all_project_caches() -> int:
    """Invalidate all project caches."""
    return project_cache.clear_prefix("project:")


# ==============================================================================
# GENERAL PURPOSE ASYNC CACHE DECORATOR
# ==============================================================================


def async_cache(prefix: str, ttl_seconds: int = 60, cache_instance: SimpleCache | None = None):
    """
    General purpose async cache decorator.

    Usage:
        @async_cache(prefix="analytics", ttl_seconds=300)
        async def get_analytics(self, user_id: uuid.UUID, period: str) -> Dict:
            ...
    """
    _cache = cache_instance or SimpleCache(default_ttl_seconds=ttl_seconds)

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip 'self' for key generation
            key_args = args[1:] if args else args
            cache_key = _cache._make_key(prefix, *key_args, **kwargs)

            # Try to get from cache
            cached = _cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute async function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                _cache.set(cache_key, result, ttl_seconds)

            return result

        # Add cache control methods to wrapper
        wrapper.invalidate = lambda *args, **kwargs: _cache.delete(  # type: ignore
            _cache._make_key(prefix, *args, **kwargs)
        )
        wrapper.clear_all = lambda: _cache.clear_prefix(prefix)  # type: ignore

        return wrapper

    return decorator
