
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import time
from uuid import uuid4

from utils.cache import (
    SimpleCache, 
    dashboard_cache, 
    cache_dashboard_stats, 
    invalidate_user_dashboard_cache,
    project_cache,
    cache_project_details,
    invalidate_project_cache,
    invalidate_all_project_caches,
    async_cache
)

# ============================================================================
# SimpleCache Tests
# ============================================================================

class TestSimpleCache:
    def test_set_and_get(self):
        cache = SimpleCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_non_existent(self):
        cache = SimpleCache()
        assert cache.get("non_existent") is None

    def test_expiration(self):
        cache = SimpleCache(default_ttl_seconds=1)
        cache.set("key1", "value1", ttl_seconds=0.1)
        time.sleep(0.15)
        # Should be expired
        assert cache.get("key1") is None

    def test_delete(self):
        cache = SimpleCache()
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("key1") is False

    def test_clear_prefix(self):
        cache = SimpleCache()
        cache.set("prefix:1", "val1")
        cache.set("prefix:2", "val2")
        cache.set("other:1", "val3")
        
        count = cache.clear_prefix("prefix:")
        assert count == 2
        assert cache.get("prefix:1") is None
        assert cache.get("other:1") == "val3"

    def test_clear_all(self):
        cache = SimpleCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        
        assert cache.clear_all() == 2
        assert cache._cache == {}

    def test_cleanup_expired(self):
        cache = SimpleCache()
        cache.set("k1", "v1", ttl_seconds=0.1)
        cache.set("k2", "v2", ttl_seconds=10)
        time.sleep(0.15)
        
        count = cache.cleanup_expired()
        assert count == 1
        assert cache.get("k2") == "v2"

    def test_make_key_consistency(self):
        cache = SimpleCache()
        key1 = cache._make_key("pref", "arg1", kw="val")
        key2 = cache._make_key("pref", "arg1", kw="val")
        assert key1 == key2
        
        # Order of kwargs shouldn't matter
        key3 = cache._make_key("pref", "arg1", a=1, b=2)
        key4 = cache._make_key("pref", "arg1", b=2, a=1)
        assert key3 == key4

# ============================================================================
# Decorator Tests
# ============================================================================

class TestDashboardCache:
    def test_cache_dashboard_stats_decorator(self):
        # Mock class to use decorator on
        class Service:
            def __init__(self):
                self.call_count = 0
                
            @cache_dashboard_stats(ttl_seconds=60)
            def get_stats(self, user_id, type="all"):
                self.call_count += 1
                return {"user": user_id, "type": type}

        service = Service()
        uid = uuid4()
        
        # First call - executes
        res1 = service.get_stats(uid, type="weekly")
        assert res1["user"] == uid
        assert service.call_count == 1
        
        # Second call - cached
        res2 = service.get_stats(uid, type="weekly")
        assert res2 == res1
        assert service.call_count == 1 # Did not increment
        
        # Different args - executes
        res3 = service.get_stats(uid, type="monthly")
        assert service.call_count == 2

    def test_invalidate_user_dashboard_cache(self):
        uid = uuid4()
        key = dashboard_cache._make_key(f"dashboard_stats:{str(uid)[:8]}", "arg")
        dashboard_cache.set(key, "data")
        
        count = invalidate_user_dashboard_cache(str(uid))
        assert count >= 1
        assert dashboard_cache.get(key) is None

class TestProjectCache:
    @pytest.mark.asyncio
    async def test_cache_project_details_async(self):
        class Service:
            def __init__(self):
                self.call_count = 0
                
            @cache_project_details(ttl_seconds=60)
            async def get_project(self, project_id):
                self.call_count += 1
                return {"id": project_id}

        service = Service()
        pid = uuid4()
        
        # First call
        res1 = await service.get_project(pid)
        assert service.call_count == 1
        
        # Second call - cached
        res2 = await service.get_project(pid)
        assert res2 == res1
        assert service.call_count == 1
        
    def test_cache_project_details_sync(self):
        class Service:
            def __init__(self):
                self.call_count = 0
                
            @cache_project_details(ttl_seconds=60)
            def get_project(self, project_id):
                self.call_count += 1
                return {"id": project_id}
                
        service = Service()
        pid = uuid4()
        
        res1 = service.get_project(pid)
        assert service.call_count == 1
        
        res2 = service.get_project(pid)
        assert res2 == res1
        assert service.call_count == 1

    def test_invalidate_project_listeners(self):
        pid = uuid4()
        key = project_cache._make_key(f"project:{str(pid)[:8]}", "arg")
        project_cache.set(key, "data")
        
        assert invalidate_project_cache(str(pid)) >= 1
        assert project_cache.get(key) is None
        
        project_cache.set("project:all", "val")
        invalidate_all_project_caches()
        assert project_cache.get("project:all") is None

class TestAsyncCacheDecorator:
    @pytest.mark.asyncio
    async def test_async_cache_generic(self):
        mock_func = AsyncMock(return_value="result")
        
        class Service:
            @async_cache(prefix="test", ttl_seconds=60)
            async def cached_method(self, arg):
                return await mock_func(arg)
        
        service = Service()
            
        res1 = await service.cached_method("x")
        res2 = await service.cached_method("x")
        
        assert mock_func.call_count == 1
        assert res1 == res2
        
        # Test invalidation
        # Note: Invalidate doesn't take 'self', just the args that form the key
        service.cached_method.invalidate("x")
        res3 = await service.cached_method("x")
        assert mock_func.call_count == 2
        
        # Test clear_all
        service.cached_method.clear_all()
        
    @pytest.mark.asyncio
    async def test_async_cache_with_kwargs(self):
        mock_func = AsyncMock()
        mock_func.side_effect = lambda x, y=0: x + y
        
        class Service:
            @async_cache(prefix="calc")
            async def calc(self, x, y=0):
                return await mock_func(x, y=y)
                
        service = Service()
            
        await service.calc(1, y=2)
        await service.calc(1, y=2)
        assert mock_func.call_count == 1
        
        await service.calc(1, y=3)
        assert mock_func.call_count == 2

