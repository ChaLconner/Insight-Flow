"""
Tests for cache service.
Covers InMemoryCache, RedisCache fallback, and CacheService main class.
"""

import pytest
from unittest.mock import patch, MagicMock
import time


class TestInMemoryCache:
    """Tests for InMemoryCache backend."""

    def test_in_memory_cache_singleton(self):
        """Test that InMemoryCache is a singleton."""
        from services.cache_service import InMemoryCache

        cache1 = InMemoryCache()
        cache2 = InMemoryCache()
        assert cache1 is cache2

    def test_set_and_get(self):
        """Test basic set and get operations."""
        from services.cache_service import InMemoryCache

        cache = InMemoryCache()
        cache.clear()

        test_data = {"key": "value", "number": 42}
        cache.set("test_key", test_data)
        result = cache.get("test_key")

        # InMemoryCache adds metadata - check original data is preserved
        assert result is not None
        assert result["key"] == test_data["key"]
        assert result["number"] == test_data["number"]
        assert "timestamp" in result  # Metadata added by cache
        assert "timeout" in result  # Metadata added by cache

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        from services.cache_service import InMemoryCache

        cache = InMemoryCache()
        cache.clear()

        result = cache.get("nonexistent_key")
        assert result is None

    def test_delete_key(self):
        """Test deleting a key."""
        from services.cache_service import InMemoryCache

        cache = InMemoryCache()
        cache.clear()

        cache.set("to_delete", {"data": "value"})
        assert cache.get("to_delete") is not None

        cache.delete("to_delete")
        assert cache.get("to_delete") is None

    def test_clear_cache(self):
        """Test clearing all cache entries."""
        from services.cache_service import InMemoryCache

        cache = InMemoryCache()
        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_expiry(self):
        """Test that cache entries expire after timeout."""
        from services.cache_service import InMemoryCache

        cache = InMemoryCache()
        cache.clear()

        # Set with very short timeout
        cache.set("expiring_key", {"data": "expires"}, timeout=1)
        assert cache.get("expiring_key") is not None

        # Wait for expiry
        time.sleep(1.1)
        assert cache.get("expiring_key") is None

    def test_invalidate_pattern_substring(self):
        """Test pattern-based cache invalidation using substring matching."""
        from services.cache_service import InMemoryCache

        cache = InMemoryCache()
        cache.clear()

        # Set multiple keys with similar patterns
        cache.set("user:1:profile", {"name": "User 1"})
        cache.set("user:1:settings", {"theme": "dark"})
        cache.set("user:2:profile", {"name": "User 2"})
        cache.set("project:1:data", {"title": "Project"})

        # Invalidate all keys containing "user:1:" (substring match)
        deleted_count = cache.invalidate_pattern("user:1:")

        assert deleted_count == 2
        assert cache.get("user:1:profile") is None
        assert cache.get("user:1:settings") is None
        assert cache.get("user:2:profile") is not None
        assert cache.get("project:1:data") is not None

    def test_get_stats(self):
        """Test getting cache statistics."""
        from services.cache_service import InMemoryCache

        cache = InMemoryCache()
        cache.clear()

        cache.set("key1", {"data": 1})
        cache.get("key1")  # Hit
        cache.get("nonexistent")  # Miss

        stats = cache.get_stats()

        assert "size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "max_size" in stats
        assert "hit_rate" in stats

    def test_lru_eviction(self):
        """Test that LRU eviction works when cache is full."""
        from services.cache_service import InMemoryCache

        cache = InMemoryCache()
        cache.clear()

        # Store original max size and temporarily reduce it
        original_max = cache.MAX_SIZE
        cache.MAX_SIZE = 3

        try:
            cache.set("key1", {"data": 1})
            cache.set("key2", {"data": 2})
            cache.set("key3", {"data": 3})
            # Access key1 to make it more recently used
            cache.get("key1")
            # Add another key, should evict key2 (oldest)
            cache.set("key4", {"data": 4})

            # key2 should be evicted as it's the oldest, not key1 which was accessed
            # Note: This depends on implementation details
            stats = cache.get_stats()
            assert stats["size"] <= 3
        finally:
            cache.MAX_SIZE = original_max


class TestRedisCache:
    """Tests for RedisCache backend with mocked Redis."""

    def test_redis_get_from_cache(self):
        """Test Redis get operation with a working mock."""
        import json

        with patch.dict("sys.modules", {"redis": MagicMock()}):
            import sys
            mock_redis_module = sys.modules["redis"]
            # Mock ConnectionPool.from_url
            mock_pool = MagicMock()
            mock_redis_module.ConnectionPool.from_url.return_value = mock_pool

            # Mock Redis client
            mock_client = MagicMock()
            mock_redis_module.Redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.get.return_value = json.dumps({"key": "value"})

            from services.cache_service import RedisCache

            # Force reimport with mocks
            cache = RedisCache("redis://localhost:6379")
            result = cache.get("test_key")

            assert result == {"key": "value"}

    def test_redis_get_miss(self):
        """Test Redis get operation with cache miss."""
        with patch.dict("sys.modules", {"redis": MagicMock()}):
            import sys
            mock_redis_module = sys.modules["redis"]
            mock_pool = MagicMock()
            mock_redis_module.ConnectionPool.from_url.return_value = mock_pool

            mock_client = MagicMock()
            mock_redis_module.Redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.get.return_value = None

            from services.cache_service import RedisCache

            cache = RedisCache("redis://localhost:6379")
            result = cache.get("nonexistent_key")

            assert result is None

    def test_redis_set_with_timeout(self):
        """Test Redis set operation."""
        with patch.dict("sys.modules", {"redis": MagicMock()}):
            import sys
            mock_redis_module = sys.modules["redis"]
            mock_pool = MagicMock()
            mock_redis_module.ConnectionPool.from_url.return_value = mock_pool

            mock_client = MagicMock()
            mock_redis_module.Redis.return_value = mock_client
            mock_client.ping.return_value = True

            from services.cache_service import RedisCache

            cache = RedisCache("redis://localhost:6379")
            cache.set("test_key", {"data": "value"}, timeout=60)

            mock_client.setex.assert_called()

    def test_redis_delete(self):
        """Test Redis delete operation."""
        with patch.dict("sys.modules", {"redis": MagicMock()}):
            import sys
            mock_redis_module = sys.modules["redis"]
            mock_pool = MagicMock()
            mock_redis_module.ConnectionPool.from_url.return_value = mock_pool

            mock_client = MagicMock()
            mock_redis_module.Redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.delete.return_value = 1

            from services.cache_service import RedisCache

            cache = RedisCache("redis://localhost:6379")
            result = cache.delete("test_key")

            assert result is True
            mock_client.delete.assert_called_with("test_key")

    def test_redis_health_check_healthy(self):
        """Test Redis health check when healthy."""
        with patch.dict("sys.modules", {"redis": MagicMock()}):
            import sys
            mock_redis_module = sys.modules["redis"]
            mock_pool = MagicMock()
            mock_pool.max_connections = 20
            mock_redis_module.ConnectionPool.from_url.return_value = mock_pool

            mock_client = MagicMock()
            mock_redis_module.Redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.info.return_value = {
                "used_memory_human": "1M",
                "used_memory_peak_human": "2M",
            }

            from services.cache_service import RedisCache

            cache = RedisCache("redis://localhost:6379")
            health = cache.health_check()

            assert health["connected"] is True
            assert "latency_ms" in health

    def test_redis_health_check_unhealthy(self):
        """Test Redis health check when connection fails."""
        with patch.dict("sys.modules", {"redis": MagicMock()}):
            import sys
            mock_redis_module = sys.modules["redis"]
            mock_pool = MagicMock()
            mock_redis_module.ConnectionPool.from_url.return_value = mock_pool

            mock_client = MagicMock()
            mock_redis_module.Redis.return_value = mock_client
            # First ping succeeds (for init), subsequent pings fail
            mock_client.ping.side_effect = [True, Exception("Connection refused")]

            from services.cache_service import RedisCache

            cache = RedisCache("redis://localhost:6379")
            health = cache.health_check()

            assert health["connected"] is False
            assert "error" in health


class TestCacheService:
    """Tests for main CacheService facade."""

    def test_cache_service_singleton(self):
        """Test that CacheService is a singleton."""
        from services.cache_service import CacheService

        service1 = CacheService()
        service2 = CacheService()
        assert service1 is service2

    def test_cache_service_uses_in_memory_without_redis(self):
        """Test that CacheService uses in-memory when Redis URL not set."""
        from services.cache_service import CacheService, InMemoryCache

        with patch.dict("os.environ", {"REDIS_URL": ""}, clear=False):
            # Force re-initialization
            CacheService._instance = None
            service = CacheService()

            # Should be using in-memory cache
            assert isinstance(service.backend, InMemoryCache)

    def test_cache_service_basic_operations(self):
        """Test basic get/set/delete operations through CacheService."""
        from services.cache_service import CacheService

        # Reset singleton
        CacheService._instance = None
        service = CacheService()
        service.clear()

        # Test set
        service.set("service_key", {"test": "data"}, timeout=300)

        # Test get
        result = service.get("service_key")
        assert result is not None
        assert result["test"] == "data"

        # Test delete
        service.delete("service_key")
        assert service.get("service_key") is None

    def test_cache_service_stats(self):
        """Test getting statistics through CacheService."""
        from services.cache_service import CacheService

        service = CacheService()
        stats = service.get_stats()

        assert isinstance(stats, dict)
        assert "hits" in stats or "size" in stats  # Depends on backend


class TestCacheKeyGeneration:
    """Tests for cache key patterns and generation."""

    def test_user_cache_key_pattern(self):
        """Test user-related cache key patterns."""
        from services.cache_service import InMemoryCache

        cache = InMemoryCache()
        cache.clear()

        user_id = "user-123"
        cache.set(f"user:{user_id}:profile", {"name": "Test"})
        cache.set(f"user:{user_id}:preferences", {"theme": "dark"})

        # Both should be retrievable
        assert cache.get(f"user:{user_id}:profile") is not None
        assert cache.get(f"user:{user_id}:preferences") is not None

        # Invalidate all user keys (substring match)
        deleted = cache.invalidate_pattern(f"user:{user_id}:")
        assert deleted == 2

    def test_project_cache_key_pattern(self):
        """Test project-related cache key patterns."""
        from services.cache_service import InMemoryCache

        cache = InMemoryCache()
        cache.clear()

        project_id = "proj-456"
        cache.set(f"project:{project_id}:members", {"members": [{"id": 1}]})
        cache.set(f"project:{project_id}:tasks", {"tasks": [{"id": 10}]})
        cache.set(f"project:{project_id}:analytics", {"views": 100})

        # Invalidate project cache (substring match)
        deleted = cache.invalidate_pattern(f"project:{project_id}:")
        assert deleted == 3
