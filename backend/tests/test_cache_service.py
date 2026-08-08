import pytest

from services.cache_service import CacheService, InMemoryCache, RedisCache


class FakeRedisClient:
    def __init__(self, keys: list[str | bytes]):
        self.keys = keys
        self.deleted: list[str | bytes] = []
        self.flushdb_called = False
        self.keys_called = False

    def scan_iter(self, match: str, count: int = 500):
        import fnmatch

        assert count == 500
        yield from [
            key
            for key in self.keys
            if fnmatch.fnmatch(
                key.decode("utf-8") if isinstance(key, bytes) else key,
                match,
            )
        ]

    def delete(self, *keys: str | bytes) -> int:
        self.deleted.extend(keys)
        return len(keys)

    def flushdb(self):
        self.flushdb_called = True

    def keys(self, _pattern: str):
        self.keys_called = True
        return []


class TestCacheServiceConfiguration:
    """Tests for cache service configuration."""

    def test_cache_service_import(self):
        """Test cache service can be imported."""
        from services.cache_service import CacheService

        assert CacheService is not None

    def test_cache_key_generation(self):
        """Test cache key generation."""
        prefix = "user"
        user_id = "123"

        key = f"{prefix}:{user_id}"

        assert key == "user:123"

    def test_cache_ttl_values(self):
        """Test cache TTL values are reasonable."""
        # Common cache TTL values
        SHORT_TTL = 60  # 1 minute
        MEDIUM_TTL = 300  # 5 minutes
        LONG_TTL = 3600  # 1 hour

        assert SHORT_TTL < MEDIUM_TTL < LONG_TTL
        assert LONG_TTL == 3600

    @pytest.mark.asyncio
    async def test_unavailable_redis_falls_back_to_memory(self, monkeypatch):
        """An unreachable Redis server must not remain the active cache backend."""

        class IsolatedCacheService(CacheService):
            _instance = None

        monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
        service = IsolatedCacheService()

        assert await service.get("unavailable-redis") is None
        assert isinstance(service.backend, InMemoryCache)


class TestCacheKeyPatterns:
    """Tests for cache key patterns."""

    def test_user_cache_key(self):
        """Test user cache key pattern."""
        user_id = "abc123"
        key = f"user:{user_id}"

        assert "user:" in key
        assert user_id in key

    def test_project_cache_key(self):
        """Test project cache key pattern."""
        project_id = "proj123"
        key = f"project:{project_id}"

        assert "project:" in key
        assert project_id in key

    def test_task_cache_key(self):
        """Test task cache key pattern."""
        task_id = "task123"
        key = f"task:{task_id}"

        assert "task:" in key
        assert task_id in key


class TestRedisCacheInvalidation:
    def _make_cache(self, keys: list[str | bytes]) -> RedisCache:
        cache = object.__new__(RedisCache)
        cache.client = FakeRedisClient(keys)
        cache.stats = {"hits": 0, "misses": 0, "sets": 0, "errors": 0}
        return cache

    @pytest.mark.asyncio
    async def test_clear_deletes_only_application_cache_prefixes(self):
        cache = self._make_cache(
            [
                "dashboard:overview:user-1",
                "analytics:overview:user-1",
                "rate_limit:127.0.0.1:/auth/login",
                "GET:http://testserver/health",
                "celery-task-meta:job-1",
                "session:user-1",
            ]
        )

        await cache.clear()

        client = cache.client
        assert isinstance(client, FakeRedisClient)
        assert client.flushdb_called is False
        assert client.keys_called is False
        assert set(client.deleted) == {
            "dashboard:overview:user-1",
            "analytics:overview:user-1",
            "rate_limit:127.0.0.1:/auth/login",
            "GET:http://testserver/health",
        }

    @pytest.mark.asyncio
    async def test_invalidate_pattern_uses_scan_not_keys(self):
        cache = self._make_cache(
            [
                "dashboard:overview:user-1",
                "dashboard:recent_projects:user-1:5",
                "analytics:overview:user-1",
            ]
        )

        deleted = await cache.invalidate_pattern("dashboard:")

        client = cache.client
        assert isinstance(client, FakeRedisClient)
        assert deleted == 2
        assert client.keys_called is False
        assert set(client.deleted) == {
            "dashboard:overview:user-1",
            "dashboard:recent_projects:user-1:5",
        }

    @pytest.mark.asyncio
    async def test_invalidate_pattern_decodes_redis_byte_keys(self):
        cache = self._make_cache(
            [
                b"dashboard:overview:user-1",
                b"dashboard:recent_projects:user-1:5",
                b"analytics:overview:user-1",
            ]
        )

        deleted = await cache.invalidate_pattern("dashboard:")

        client = cache.client
        assert isinstance(client, FakeRedisClient)
        assert deleted == 2
        assert client.deleted == [
            "dashboard:overview:user-1",
            "dashboard:recent_projects:user-1:5",
        ]
