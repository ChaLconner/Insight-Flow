"""
Cache service with Redis support and fallback to in-memory cache.
Provides statistics tracking and pattern-based invalidation.
"""
import time
import json
import os
from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from utils.logger import setup_logger

logger = setup_logger("cache_service")


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Dict[str, Any], timeout: Optional[int] = None) -> None:
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


class InMemoryCache(CacheBackend):
    """Thread-safe in-memory cache with LRU eviction."""
    
    _instance = None
    MAX_SIZE = 1000

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InMemoryCache, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_timeout = 300
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0
        }
        import threading
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
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

    def set(self, key: str, value: Dict[str, Any], timeout: Optional[int] = None) -> None:
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
                "timeout": timeout if timeout is not None else self.default_timeout
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
            keys_to_remove = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self.cache[key]
            logger.debug(f"Invalidated {len(keys_to_remove)} keys matching '{pattern}'")
            return len(keys_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            return {
                **self.stats,
                "size": len(self.cache),
                "max_size": self.MAX_SIZE,
                "hit_rate": round(hit_rate, 2)
            }


class RedisCache(CacheBackend):
    """Redis-based cache backend."""
    
    def __init__(self, redis_url: str, default_timeout: int = 300):
        self.default_timeout = default_timeout
        self.stats = {"hits": 0, "misses": 0, "sets": 0}
        
        try:
            import redis
            self.client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.client.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            data = self.client.get(key)
            if data:
                self.stats["hits"] += 1
                return json.loads(data)
            self.stats["misses"] += 1
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Dict[str, Any], timeout: Optional[int] = None) -> None:
        try:
            ttl = timeout if timeout is not None else self.default_timeout
            self.client.setex(key, ttl, json.dumps(value, default=str))
            self.stats["sets"] += 1
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, key: str) -> bool:
        try:
            return self.client.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def clear(self) -> None:
        try:
            self.client.flushdb()
            logger.info("Redis cache cleared")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    def invalidate_pattern(self, pattern: str) -> int:
        try:
            keys = self.client.keys(f"*{pattern}*")
            if keys:
                count = self.client.delete(*keys)
                logger.debug(f"Invalidated {count} Redis keys matching '{pattern}'")
                return count
            return 0
        except Exception as e:
            logger.error(f"Redis invalidate_pattern error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        return {
            **self.stats,
            "backend": "redis",
            "hit_rate": round(hit_rate, 2)
        }


class CacheService:
    """
    Main cache service that auto-selects backend.
    Falls back to in-memory cache if Redis is not available.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
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
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self.backend.get(key)
    
    def set(self, key: str, value: Dict[str, Any], timeout: Optional[int] = None) -> None:
        self.backend.set(key, value, timeout)
    
    def delete(self, key: str) -> bool:
        return self.backend.delete(key)
    
    def clear(self) -> None:
        self.backend.clear()
    
    def invalidate_pattern(self, pattern: str) -> int:
        return self.backend.invalidate_pattern(pattern)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if hasattr(self.backend, 'get_stats'):
            return self.backend.get_stats()
        return {}


# Global singleton instance
cache_service = CacheService()

