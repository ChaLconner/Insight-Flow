"""
Cache service with Redis support and fallback to in-memory cache.
Provides statistics tracking and pattern-based invalidation.
"""

import json
import os
import time
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from utils.logger import setup_logger

logger = setup_logger("cache_service")

APP_CACHE_PREFIXES = (
    "dashboard:",
    "analytics:",
    "rate_limit:",
    "GET:",
)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: str) -> dict[str, Any] | None:
        """Get a value from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: dict[str, Any], timeout: int | None = None) -> None:
        """Set a value in cache."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern. Returns count of deleted keys."""
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        pass


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

    def get(self, key: str) -> dict[str, Any] | None:
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

    def set(self, key: str, value: dict[str, Any], timeout: int | None = None) -> None:
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
                "timeout": timeout if timeout is not None else self.default_timeout,
            }
            self.stats["sets"] += 1

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            count = len(self.cache)
            self.cache.clear()
        logger.info(f"Cache cleared ({count} entries)")

    def invalidate_pattern(self, pattern: str) -> int:
        with self._lock:
            keys_to_remove = [key for key in self.cache if pattern in key]
            for key in keys_to_remove:
                del self.cache[key]
            logger.debug(f"Invalidated {len(keys_to_remove)} keys matching '{pattern}'")
            return len(keys_to_remove)

    def get_stats(self) -> dict[str, Any]:
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
    """Redis-based cache backend with connection pooling and health checks."""

    def __init__(self, redis_url: str, default_timeout: int = 300):
        self.default_timeout = default_timeout
        self.redis_url = redis_url
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "errors": 0}
        self._connected = False

        try:
            import redis
            from redis import ConnectionPool

            # Create connection pool for better performance
            self.pool = ConnectionPool.from_url(
                redis_url,
                max_connections=20,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            self.client.ping()
            self._connected = True
            logger.info("Redis cache connected successfully with connection pooling")
        except ImportError:
            logger.error("Redis package not installed. Run: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _execute_with_retry(self, operation, *args, max_retries: int = 2, **kwargs):
        """Execute Redis operation with retry logic."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                self.stats["errors"] += 1
                if attempt < max_retries:
                    logger.warning(f"Redis operation failed (attempt {attempt + 1}), retrying: {e}")
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
        logger.error(f"Redis operation failed after {max_retries + 1} attempts: {last_error}")
        return None

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            data = self._execute_with_retry(self.client.get, key)
            if data:
                self.stats["hits"] += 1
                return dict(json.loads(data))
            self.stats["misses"] += 1
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self.stats["errors"] += 1
            return None

    def set(self, key: str, value: dict[str, Any], timeout: int | None = None) -> None:
        try:
            ttl = timeout if timeout is not None else self.default_timeout
            serialized = json.dumps(value, default=str)
            self._execute_with_retry(self.client.setex, key, ttl, serialized)
            self.stats["sets"] += 1
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            self.stats["errors"] += 1

    def delete(self, key: str) -> bool:
        try:
            result = self._execute_with_retry(self.client.delete, key)
            return result > 0 if result else False
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def clear(self) -> None:
        try:
            deleted = 0
            for prefix in APP_CACHE_PREFIXES:
                deleted += self._delete_matching_keys(f"{prefix}*")
            logger.info(f"Redis app cache cleared ({deleted} entries)")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    def invalidate_pattern(self, pattern: str) -> int:
        try:
            count = self._delete_matching_keys(f"*{pattern}*")
            logger.debug(f"Invalidated {count} Redis keys matching '{pattern}'")
            return count
        except Exception as e:
            logger.error(f"Redis invalidate_pattern error: {e}")
            return 0

    def _iter_keys(self, match: str) -> Iterable[str]:
        scan_iter = getattr(self.client, "scan_iter", None)
        if callable(scan_iter):
            yield from scan_iter(match=match, count=500)
            return

        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor=cursor, match=match, count=500)
            yield from keys
            if cursor == 0:
                break

    def _delete_matching_keys(self, match: str) -> int:
        deleted = 0
        batch: list[str] = []

        for key in self._iter_keys(match):
            batch.append(key)
            if len(batch) >= 500:
                deleted += self._delete_batch(batch)
                batch.clear()

        if batch:
            deleted += self._delete_batch(batch)

        return deleted

    def _delete_batch(self, keys: list[str]) -> int:
        count = self._execute_with_retry(self.client.delete, *keys)
        return int(count or 0)

    def health_check(self) -> dict[str, Any]:
        """Check Redis connection health and return detailed info."""
        try:
            start = time.time()
            self.client.ping()
            latency_ms = round((time.time() - start) * 1000, 2)

            # Get Redis info
            info: dict[str, Any] = self.client.info(section="memory")  # type: ignore

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

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics including health info."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        health = self.health_check()

        return {**self.stats, "backend": "redis", "hit_rate": round(hit_rate, 2), "health": health}


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
        redis_url = os.getenv("REDIS_URL")

        if redis_url:
            try:
                self.backend = RedisCache(redis_url)
                logger.info("Using Redis cache backend")
            except Exception:
                logger.warning("Redis unavailable, falling back to in-memory cache")
                self.backend = InMemoryCache()
        else:
            self.backend = InMemoryCache()
            logger.info("Using in-memory cache backend")

    def get(self, key: str) -> dict[str, Any] | None:
        return self.backend.get(key)

    def set(self, key: str, value: dict[str, Any], timeout: int | None = None) -> None:
        self.backend.set(key, value, timeout)

    def delete(self, key: str) -> bool:
        return self.backend.delete(key)

    def clear(self) -> None:
        self.backend.clear()

    def invalidate_pattern(self, pattern: str) -> int:
        return self.backend.invalidate_pattern(pattern)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if hasattr(self.backend, "get_stats"):
            return self.backend.get_stats()
        return {}


# Global singleton instance
cache_service = CacheService()
