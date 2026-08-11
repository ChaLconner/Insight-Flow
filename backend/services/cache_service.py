"""
Cache service with Redis support and fallback to in-memory cache.
Provides statistics tracking and pattern-based invalidation.
"""

import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterable
from typing import Any, cast

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger("cache_service")

APP_CACHE_PREFIXES = (
    "auth:",
    "blacklist:",
    "dashboard:",
    "analytics:",
    "rate_limit:",
    "GET:",
)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> dict[str, Any] | None:
        """Get a value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Set a value in cache."""
        pass

    @abstractmethod
    async def increment_with_window(self, key: str, window_seconds: int) -> int:
        """Atomically increment a counter and apply its first-write expiry."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern. Returns count of deleted keys."""
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        pass


class DisabledCache(CacheBackend):
    """Explicitly disabled cache backend used when CACHE_ENABLED is false."""

    async def get(self, _key: str) -> dict[str, Any] | None:
        return None

    async def set(self, _key: str, _value: dict[str, Any], _ttl: int | None = None) -> None:
        return None

    async def increment_with_window(self, _key: str, _window_seconds: int) -> int:
        # CacheService.increment_with_window falls back to its local counter
        # backend for rate limiting when the shared cache is disabled.
        raise RuntimeError("Cache is disabled")

    async def delete(self, _key: str) -> bool:
        return False

    async def clear(self) -> None:
        return None

    async def invalidate_pattern(self, _pattern: str) -> int:
        return 0

    async def get_stats(self) -> dict[str, Any]:
        return {"hits": 0, "misses": 0, "sets": 0, "size": 0, "disabled": True}


class InMemoryCache(CacheBackend):
    """Thread-safe in-memory cache with LRU eviction."""

    _instance = None
    MAX_SIZE = 1000

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.cache: dict[str, dict[str, Any]] = {}
        self.default_timeout = 300
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}
        import threading

        self._lock = threading.Lock()

    async def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            if key in self.cache:
                cached_data = self.cache[key]
                current_time = time.time()

                timeout = cached_data.get("timeout", self.default_timeout)

                if current_time - cached_data["timestamp"] < timeout:
                    self.stats["hits"] += 1
                    # Move to end for LRU
                    self.cache[key] = self.cache.pop(key)
                    return cached_data
                else:
                    del self.cache[key]

            self.stats["misses"] += 1
            return None

    async def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        with self._lock:
            # LRU eviction if full
            while len(self.cache) >= self.MAX_SIZE and key not in self.cache:
                try:
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    self.stats["evictions"] += 1
                except StopIteration:
                    break

            self.cache[key] = {
                **value,
                "timestamp": time.time(),
                "timeout": ttl if ttl is not None else self.default_timeout,
            }
            self.stats["sets"] += 1

    async def increment_with_window(self, key: str, window_seconds: int) -> int:
        """Atomically increment a fixed-window counter in the process."""
        if window_seconds <= 0:
            raise ValueError("Cache counter timeout must be greater than zero")
        with self._lock:
            current_time = time.time()
            cached_data = self.cache.get(key)
            if cached_data is None or current_time - cached_data["timestamp"] >= cached_data.get(
                "timeout", self.default_timeout
            ):
                count = 1
            else:
                count = int(cached_data.get("content", {}).get("count", 0)) + 1

            self.cache[key] = {
                "content": {"count": count},
                "timestamp": current_time,
                "timeout": window_seconds,
            }
            self.stats["sets"] += 1
            return count

    async def delete(self, key: str) -> bool:
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    async def clear(self) -> None:
        with self._lock:
            count = len(self.cache)
            self.cache.clear()
        logger.info(f"Cache cleared ({count} entries)")

    async def invalidate_pattern(self, pattern: str) -> int:
        with self._lock:
            keys_to_remove = [key for key in self.cache if pattern in key]
            for key in keys_to_remove:
                del self.cache[key]
            logger.debug(f"Invalidated {len(keys_to_remove)} keys matching '{pattern}'")
            return len(keys_to_remove)

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            return {
                **self.stats,
                "size": len(self.cache),
                "max_size": self.MAX_SIZE,
                "hit_rate": round(hit_rate, 2),
            }


class RedisCache(CacheBackend):
    """Redis-based cache backend with connection pooling and health checks (async)."""

    def __init__(self, redis_url: str, default_timeout: int = 300, password: str | None = None):
        self.default_timeout = default_timeout
        self.redis_url = redis_url
        self.password = password
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "errors": 0}
        self._connected = False
        self._connection_checked = False
        self._connection_lock = asyncio.Lock()
        self._last_connection_check = 0.0
        self._connection_check_interval = 30.0

        try:
            import redis.asyncio as redis
            from redis.asyncio import ConnectionPool

            # Create connection pool for better performance
            self.pool: Any = ConnectionPool.from_url(
                redis_url,
                password=password,
                max_connections=20,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            self.client = redis.Redis(connection_pool=self.pool)
            logger.info("Redis async cache initialized with connection pooling")
        except ImportError:
            logger.error("Redis package not installed. Run: pip install redis")
            raise
        except Exception as e:
            logger.exception(f"Failed to initialize Redis: {e}")
            raise

    async def ensure_connected(self) -> bool:
        """Check Redis lazily with a bounded reconnect cadence."""
        now = time.monotonic()
        if (
            self._connection_checked
            and now - self._last_connection_check < self._connection_check_interval
        ):
            return self._connected

        async with self._connection_lock:
            now = time.monotonic()
            if (
                self._connection_checked
                and now - self._last_connection_check < self._connection_check_interval
            ):
                return self._connected

            self._connection_checked = True
            self._last_connection_check = now
            try:
                await self.client.ping()
                self._connected = True
                return True
            except Exception as e:
                self._connected = False
                logger.warning(f"Redis unavailable, using in-memory cache: {e}")
                return False

    async def _execute_with_retry(self, operation, *args, max_retries: int = 2, **kwargs):
        """Execute Redis operation with non-blocking retry logic."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                res = operation(*args, **kwargs)
                if asyncio.iscoroutine(res):
                    return await res
                return res
            except Exception as e:
                last_error = e
                self._connected = False
                self._connection_checked = False
                self._last_connection_check = 0.0
                self.stats["errors"] += 1
                if attempt < max_retries:
                    logger.warning(f"Redis operation failed (attempt {attempt + 1}), retrying: {e}")
                    await asyncio.sleep(0.1 * (attempt + 1))  # Async non-blocking backoff
        logger.error(f"Redis operation failed after {max_retries + 1} attempts: {last_error}")
        return None

    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            data = await self._execute_with_retry(self.client.get, key)
            if data:
                self.stats["hits"] += 1
                return dict(json.loads(data))
            self.stats["misses"] += 1
            return None
        except Exception as e:
            logger.exception(f"Redis get error: {e}")
            self.stats["errors"] += 1
            return None

    async def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        try:
            cache_ttl = ttl if ttl is not None else self.default_timeout
            serialized = json.dumps(value, default=str)
            await self._execute_with_retry(self.client.setex, key, cache_ttl, serialized)
            self.stats["sets"] += 1
        except Exception as e:
            logger.exception(f"Redis set error: {e}")
            self.stats["errors"] += 1

    async def increment_with_window(self, key: str, window_seconds: int) -> int:
        """Atomically increment a Redis counter using a Lua fixed-window script."""
        if window_seconds <= 0:
            raise ValueError("Cache counter timeout must be greater than zero")

        script = """
        local current = redis.call('INCR', KEYS[1])
        if current == 1 then
            redis.call('EXPIRE', KEYS[1], ARGV[1])
        end
        return current
        """
        result = await self._execute_with_retry(self.client.eval, script, 1, key, window_seconds)
        if result is None:
            raise ConnectionError("Redis counter operation failed")
        return int(result)

    async def delete(self, key: str) -> bool:
        try:
            result = await self._execute_with_retry(self.client.delete, key)
            return result > 0 if result else False
        except Exception as e:
            logger.exception(f"Redis delete error: {e}")
            return False

    async def clear(self) -> None:
        try:
            deleted = 0
            for prefix in APP_CACHE_PREFIXES:
                deleted += await self._delete_matching_keys(f"{prefix}*")
            logger.info(f"Redis app cache cleared ({deleted} entries)")
        except Exception as e:
            logger.exception(f"Redis clear error: {e}")

    async def invalidate_pattern(self, pattern: str) -> int:
        try:
            count = await self._delete_matching_keys(f"*{pattern}*")
            logger.debug(f"Invalidated {count} Redis keys matching '{pattern}'")
            return count
        except Exception as e:
            logger.exception(f"Redis invalidate_pattern error: {e}")
            return 0

    async def _iter_scan_iter_keys(self, scan_iter, match: str) -> AsyncIterable[str]:
        """Yield keys from clients exposing scan_iter in either async or sync form."""
        result = scan_iter(match=match, count=500)
        if hasattr(result, "__aiter__"):
            async for key in result:
                yield key.decode("utf-8") if isinstance(key, bytes) else str(key)
            return
        for key in result:
            yield key.decode("utf-8") if isinstance(key, bytes) else str(key)

    async def _iter_scan_cursor_keys(self, match: str) -> AsyncIterable[str]:
        """Yield keys from clients exposing the cursor-based scan API."""
        cursor = 0
        while True:
            result: Any = self.client.scan(cursor=cursor, match=match, count=500)
            if asyncio.iscoroutine(result):
                cursor, keys = await result
            else:
                cursor, keys = cast("tuple[Any, Any]", result)
            for key in keys:
                yield key.decode("utf-8") if isinstance(key, bytes) else str(key)
            if int(cursor) == 0:
                break

    async def _iter_keys(self, match: str) -> AsyncIterable[str]:
        scan_iter = getattr(self.client, "scan_iter", None)
        if callable(scan_iter):
            async for key in self._iter_scan_iter_keys(scan_iter, match):
                yield key
            return
        async for key in self._iter_scan_cursor_keys(match):
            yield key

    async def _delete_matching_keys(self, match: str) -> int:
        deleted = 0
        batch: list[str] = []

        async for key in self._iter_keys(match):
            batch.append(key)
            if len(batch) >= 500:
                deleted += await self._delete_batch(batch)
                batch.clear()

        if batch:
            deleted += await self._delete_batch(batch)

        return deleted

    async def _delete_batch(self, keys: list[str]) -> int:
        count = await self._execute_with_retry(self.client.delete, *keys)
        return int(count or 0)

    async def health_check(self) -> dict[str, Any]:
        """Check Redis connection health and return detailed info."""
        try:
            start = time.time()
            res = self.client.ping()
            if asyncio.iscoroutine(res):
                await res
            latency_ms = round((time.time() - start) * 1000, 2)

            info_res: Any = self.client.info(section="memory")
            if asyncio.iscoroutine(info_res):
                info = await info_res
            else:
                info = cast("dict[str, Any]", info_res)

            return {
                "status": "healthy",
                "connected": True,
                "latency_ms": latency_ms,
                "used_memory": info.get("used_memory_human", "unknown"),
                "used_memory_peak": info.get("used_memory_peak_human", "unknown"),
                "pool_size": self.pool.max_connections if hasattr(self, "pool") else "unknown",
            }
        except Exception as e:
            return {"status": "unhealthy", "connected": False, "error": str(e)}

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics including health info."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        health = await self.health_check()

        return {**self.stats, "backend": "redis", "hit_rate": round(hit_rate, 2), "health": health}

    async def close(self) -> None:
        """Release Redis client and pool resources during application shutdown."""
        close = getattr(self.client, "aclose", None)
        if close is not None:
            await close()
            return
        disconnect = getattr(self.pool, "disconnect", None)
        if disconnect is not None:
            result = disconnect()
            if asyncio.iscoroutine(result):
                await result


class CacheService:
    """
    Main cache service that auto-selects backend.
    Falls back to in-memory cache if Redis is not available.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.backend: CacheBackend
        self.redis_backend: RedisCache | None = None
        self.memory_backend = InMemoryCache()

        try:
            cache_settings = get_settings().cache
            enabled = bool(cache_settings.enabled)
            redis_url = os.getenv("REDIS_URL") or cache_settings.redis_url
            redis_password = os.getenv("REDIS_PASSWORD") or cache_settings.redis_password
            default_timeout = cache_settings.default_timeout
        except Exception:
            # Keep imports usable for small CLI tools and isolated unit tests
            # that intentionally do not configure the full application.
            redis_url = os.getenv("REDIS_URL")
            redis_password = os.getenv("REDIS_PASSWORD")
            default_timeout = 300
            enabled = True

        if not enabled:
            self.backend = DisabledCache()
            logger.info("Cache disabled by CACHE_ENABLED=false")
            return

        if redis_url:
            try:
                self.redis_backend = RedisCache(
                    redis_url,
                    default_timeout=default_timeout,
                    password=redis_password,
                )
                self.backend = self.redis_backend
                logger.info("Using Redis cache backend")
            except Exception:
                logger.warning("Redis unavailable, falling back to in-memory cache")
                self.backend = self.memory_backend
        else:
            self.backend = self.memory_backend
            logger.info("Using in-memory cache backend")

    async def _get_backend(self) -> CacheBackend:
        """Return Redis when healthy and temporarily use memory during outages."""
        if self.redis_backend is not None:
            if await self.redis_backend.ensure_connected():
                if self.backend is not self.redis_backend:
                    logger.info("Redis recovered; restoring distributed cache backend")
                    self.backend = self.redis_backend
            elif self.backend is not self.memory_backend:
                self.backend = self.memory_backend
                logger.warning("Redis unavailable, falling back to in-memory cache")
        return self.backend

    async def ensure_connected(self) -> bool:
        """Check the configured distributed backend without changing callers."""
        if self.redis_backend is None:
            return False
        return await self.redis_backend.ensure_connected()

    async def close(self) -> None:
        """Close the distributed backend, if configured."""
        if self.redis_backend is not None:
            await self.redis_backend.close()

    async def get(self, key: str) -> dict[str, Any] | None:
        backend = await self._get_backend()
        return await backend.get(key)

    async def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        backend = await self._get_backend()
        await backend.set(key, value, ttl)

    async def increment_with_window(
        self,
        key: str,
        window_seconds: int,
        *,
        fail_closed: bool = False,
    ) -> int:
        """Increment a counter atomically, optionally refusing memory fallback."""
        backend = await self._get_backend()
        try:
            return await backend.increment_with_window(key, window_seconds)
        except Exception:
            if fail_closed:
                raise
            if not isinstance(self.backend, DisabledCache):
                self.backend = self.memory_backend
                logger.warning("Cache counter unavailable; using in-memory rate-limit counter")
            return await self.memory_backend.increment_with_window(key, window_seconds)

    async def delete(self, key: str) -> bool:
        backend = await self._get_backend()
        return await backend.delete(key)

    async def clear(self) -> None:
        backend = await self._get_backend()
        await backend.clear()

    async def invalidate_pattern(self, pattern: str) -> int:
        backend = await self._get_backend()
        return await backend.invalidate_pattern(pattern)

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if self.redis_backend is not None and not await self.redis_backend.ensure_connected():
            memory_stats = await self.memory_backend.get_stats()
            return {
                **memory_stats,
                "backend": "memory-fallback",
                "health": {
                    "status": "unhealthy",
                    "connected": False,
                    "reason": "Redis is unavailable",
                },
            }
        backend = await self._get_backend()
        if hasattr(backend, "get_stats"):
            return await backend.get_stats()
        return {}


# Global singleton instance
cache_service = CacheService()
