"""
Comprehensive tests for Distributed Lock Manager.

Tests both InMemoryLockManager and RedisLockManager implementations,
including edge cases, race conditions, and error handling.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from security.distributed_locks import (
    InMemoryLockManager,
    RedisLockManager,
    get_lock_manager,
    set_lock_manager,
    reset_lock_manager,
    payment_lock,
    resource_lock,
)


# ============================================================================
# InMemoryLockManager Tests
# ============================================================================

class TestInMemoryLockManager:
    """Tests for the in-memory lock manager."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh lock manager for each test."""
        return InMemoryLockManager()
    
    @pytest.mark.asyncio
    async def test_acquire_and_release_lock(self, manager):
        """Test basic lock acquisition and release."""
        lock_key = "test:user123"
        
        async with manager.acquire(lock_key):
            assert await manager.is_locked(lock_key)
        
        # Lock should be released after context exit
        assert not await manager.is_locked(lock_key)
    
    @pytest.mark.asyncio
    async def test_lock_prevents_concurrent_access(self, manager):
        """Test that lock prevents concurrent access to same key."""
        lock_key = "test:user123"
        execution_order = []
        
        async def task(name: str, delay: float):
            async with manager.acquire(lock_key):
                execution_order.append(f"{name}_start")
                await asyncio.sleep(delay)
                execution_order.append(f"{name}_end")
        
        # Start two tasks that try to acquire the same lock
        await asyncio.gather(
            task("task1", 0.1),
            task("task2", 0.1)
        )
        
        # Tasks should execute sequentially, not interleaved
        assert execution_order == ["task1_start", "task1_end", "task2_start", "task2_end"] or \
               execution_order == ["task2_start", "task2_end", "task1_start", "task1_end"]
    
    @pytest.mark.asyncio
    async def test_different_keys_can_lock_simultaneously(self, manager):
        """Test that different keys can be locked at the same time."""
        results = []
        
        async def task(key: str, name: str):
            async with manager.acquire(key):
                results.append(f"{name}_start")
                await asyncio.sleep(0.05)
                results.append(f"{name}_end")
        
        # Start tasks with different keys
        await asyncio.gather(
            task("user:1", "task1"),
            task("user:2", "task2")
        )
        
        # Both should start before either ends (parallel execution)
        assert "task1_start" in results[:2]
        assert "task2_start" in results[:2]
    
    @pytest.mark.asyncio
    async def test_lock_timeout(self, manager):
        """Test that lock acquisition times out if held too long."""
        lock_key = "test:timeout"
        
        async def holder():
            async with manager.acquire(lock_key):
                await asyncio.sleep(2)  # Hold lock for 2 seconds
        
        async def waiter():
            await asyncio.sleep(0.1)  # Let holder acquire first
            async with manager.acquire(lock_key, timeout=0.5):
                pass  # Should timeout before getting here
        
        holder_task = asyncio.create_task(holder())
        
        with pytest.raises(TimeoutError) as exc_info:
            await waiter()
        
        assert "Another payment operation" in str(exc_info.value)
        holder_task.cancel()
        try:
            await holder_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_lock_released_on_exception(self, manager):
        """Test that lock is released even if exception occurs."""
        lock_key = "test:exception"
        
        with pytest.raises(ValueError):
            async with manager.acquire(lock_key):
                raise ValueError("Test error")
        
        # Lock should still be released
        assert not await manager.is_locked(lock_key)
    
    @pytest.mark.asyncio
    async def test_is_locked(self, manager):
        """Test is_locked method."""
        lock_key = "test:check"
        
        # Not locked yet
        assert not await manager.is_locked(lock_key)
        
        async with manager.acquire(lock_key):
            # Now locked
            assert await manager.is_locked(lock_key)
        
        # Released
        assert not await manager.is_locked(lock_key)
    
    def test_cleanup_old_locks(self, manager):
        """Test cleanup of unused locks."""
        # This is a sync test since cleanup_old_locks is sync
        # Just verify it doesn't crash
        manager.cleanup_old_locks()


# ============================================================================
# RedisLockManager Tests (Mocked)
# ============================================================================

class TestRedisLockManagerMocked:
    """Tests for Redis lock manager with mocked Redis."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = AsyncMock()
        mock.set = AsyncMock(return_value=True)
        mock.exists = AsyncMock(return_value=0)
        mock.register_script = MagicMock(return_value=AsyncMock(return_value=1))
        return mock
    
    @pytest.mark.asyncio
    async def test_acquire_calls_redis_set_nx(self, mock_redis):
        """Test that acquire uses SET NX for atomic lock."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            manager = RedisLockManager("redis://localhost:6379")
            
            async with manager.acquire("test:key"):
                pass
            
            # Verify SET was called with NX and EX
            mock_redis.set.assert_called()
            call_kwargs = mock_redis.set.call_args[1]
            assert call_kwargs.get('nx') is True
            assert call_kwargs.get('ex') == 60  # Default TTL
    
    @pytest.mark.asyncio
    async def test_acquire_timeout_on_contention(self, mock_redis):
        """Test timeout when lock is already held."""
        mock_redis.set = AsyncMock(return_value=False)  # Lock already held
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            manager = RedisLockManager("redis://localhost:6379")
            
            with pytest.raises(TimeoutError):
                async with manager.acquire("test:key", timeout=0.5):
                    pass
    
    @pytest.mark.asyncio
    async def test_release_uses_lua_script(self, mock_redis):
        """Test that release uses Lua script for safe release."""
        release_script = AsyncMock(return_value=1)
        mock_redis.register_script = MagicMock(return_value=release_script)
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            manager = RedisLockManager("redis://localhost:6379")
            
            async with manager.acquire("test:key"):
                pass
            
            # Verify release script was called
            release_script.assert_called()
    
    @pytest.mark.asyncio
    async def test_is_locked_checks_redis(self, mock_redis):
        """Test is_locked queries Redis."""
        mock_redis.exists = AsyncMock(return_value=1)
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            manager = RedisLockManager("redis://localhost:6379")
            
            result = await manager.is_locked("test:key")
            
            assert result is True
            mock_redis.exists.assert_called_with("payment_lock:test:key")


# ============================================================================
# Lock Manager Factory Tests
# ============================================================================

class TestLockManagerFactory:
    """Tests for lock manager factory functions."""
    
    def setup_method(self):
        """Reset lock manager before each test."""
        reset_lock_manager()
    
    def teardown_method(self):
        """Reset lock manager after each test."""
        reset_lock_manager()
    
    def test_get_lock_manager_returns_in_memory_by_default(self):
        """Test that in-memory manager is used when REDIS_URL not set."""
        with patch.dict('os.environ', {}, clear=True):
            reset_lock_manager()
            manager = get_lock_manager()
            assert isinstance(manager, InMemoryLockManager)
    
    def test_get_lock_manager_uses_redis_when_configured(self):
        """Test that Redis manager is used when REDIS_URL is set."""
        with patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'}):
            with patch('security.distributed_locks.RedisLockManager') as mock_redis:
                mock_redis.return_value = MagicMock()
                reset_lock_manager()
                manager = get_lock_manager()
                mock_redis.assert_called_with('redis://localhost:6379')
    
    def test_set_lock_manager_overrides_default(self):
        """Test that set_lock_manager allows custom manager."""
        custom_manager = MagicMock()
        set_lock_manager(custom_manager)
        
        assert get_lock_manager() is custom_manager


# ============================================================================
# Convenience Function Tests
# ============================================================================

class TestConvenienceFunctions:
    """Tests for payment_lock and resource_lock convenience functions."""
    
    def setup_method(self):
        reset_lock_manager()
        set_lock_manager(InMemoryLockManager())
    
    def teardown_method(self):
        reset_lock_manager()
    
    @pytest.mark.asyncio
    async def test_payment_lock_creates_user_scoped_key(self):
        """Test payment_lock creates correct lock key."""
        user_id = uuid4()
        manager = get_lock_manager()
        
        async with payment_lock(user_id, "subscription"):
            assert await manager.is_locked(f"subscription:{user_id}")
    
    @pytest.mark.asyncio
    async def test_resource_lock_creates_correct_key(self):
        """Test resource_lock creates correct lock key."""
        manager = get_lock_manager()
        
        async with resource_lock("invoice", "inv_123"):
            assert await manager.is_locked("invoice:inv_123")
    
    @pytest.mark.asyncio
    async def test_payment_lock_prevents_concurrent_same_user(self):
        """Test payment_lock prevents concurrent operations for same user."""
        user_id = uuid4()
        execution_order = []
        
        async def operation(name: str):
            async with payment_lock(user_id, "subscription"):
                execution_order.append(f"{name}_start")
                await asyncio.sleep(0.05)
                execution_order.append(f"{name}_end")
        
        await asyncio.gather(
            operation("op1"),
            operation("op2")
        )
        
        # Should be sequential
        assert execution_order[0].endswith("_start")
        assert execution_order[1].endswith("_end")
        assert execution_order[2].endswith("_start")
        assert execution_order[3].endswith("_end")
    
    @pytest.mark.asyncio
    async def test_payment_lock_allows_different_users(self):
        """Test payment_lock allows concurrent operations for different users."""
        user1 = uuid4()
        user2 = uuid4()
        concurrent_execution = False
        
        async def operation(user_id, name: str):
            nonlocal concurrent_execution
            async with payment_lock(user_id, "subscription"):
                await asyncio.sleep(0.05)
                # Check if both are running concurrently
                manager = get_lock_manager()
                other_user = user2 if user_id == user1 else user1
                if await manager.is_locked(f"subscription:{other_user}"):
                    concurrent_execution = True
        
        await asyncio.gather(
            operation(user1, "op1"),
            operation(user2, "op2")
        )
        
        assert concurrent_execution, "Different users should be able to lock concurrently"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def setup_method(self):
        reset_lock_manager()
    
    def teardown_method(self):
        reset_lock_manager()
    
    @pytest.mark.asyncio
    async def test_nested_locks_different_operations(self):
        """Test nested locks with different operations work correctly."""
        user_id = uuid4()
        set_lock_manager(InMemoryLockManager())
        
        async with payment_lock(user_id, "subscription"):
            async with payment_lock(user_id, "payment_method"):
                # Both locks should be held
                manager = get_lock_manager()
                assert await manager.is_locked(f"subscription:{user_id}")
                assert await manager.is_locked(f"payment_method:{user_id}")
    
    @pytest.mark.asyncio
    async def test_lock_manager_handles_many_concurrent_requests(self):
        """Stress test with many concurrent requests."""
        set_lock_manager(InMemoryLockManager())
        user_id = uuid4()
        counter = 0
        
        async def increment():
            nonlocal counter
            async with payment_lock(user_id, "counter"):
                current = counter
                await asyncio.sleep(0.001)  # Simulate work
                counter = current + 1
        
        # Run 50 concurrent increments
        await asyncio.gather(*[increment() for _ in range(50)])
        
        # If locking works, counter should be exactly 50
        assert counter == 50
    
    @pytest.mark.asyncio
    async def test_timeout_value_respected(self):
        """Test that custom timeout values are respected."""
        set_lock_manager(InMemoryLockManager())
        manager = get_lock_manager()
        lock_key = "test:timeout"
        
        async def holder():
            async with manager.acquire(lock_key):
                await asyncio.sleep(5)
        
        holder_task = asyncio.create_task(holder())
        await asyncio.sleep(0.1)  # Let holder acquire
        
        import time
        start = time.time()
        
        with pytest.raises(TimeoutError):
            async with manager.acquire(lock_key, timeout=0.3):
                pass
        
        elapsed = time.time() - start
        assert 0.2 < elapsed < 0.5  # Should timeout around 0.3s
        
        holder_task.cancel()
        try:
            await holder_task
        except asyncio.CancelledError:
            pass


# ============================================================================
# Integration-like Tests
# ============================================================================

class TestIntegrationScenarios:
    """Integration-like tests simulating real usage patterns."""
    
    def setup_method(self):
        reset_lock_manager()
        set_lock_manager(InMemoryLockManager())
    
    def teardown_method(self):
        reset_lock_manager()
    
    @pytest.mark.asyncio
    async def test_subscription_update_scenario(self):
        """Simulate concurrent subscription updates."""
        user_id = uuid4()
        subscription_status = {"plan": "free", "updates": 0}
        
        async def update_subscription(new_plan: str):
            async with payment_lock(user_id, "subscription"):
                # Simulate reading current state
                current = subscription_status["plan"]
                await asyncio.sleep(0.01)  # Simulate DB read
                
                # Simulate update
                subscription_status["plan"] = new_plan
                subscription_status["updates"] += 1
                await asyncio.sleep(0.01)  # Simulate DB write
        
        # Try to upgrade and downgrade concurrently
        await asyncio.gather(
            update_subscription("pro"),
            update_subscription("starter"),
            update_subscription("enterprise")
        )
        
        # Should have 3 updates, executed sequentially
        assert subscription_status["updates"] == 3
        # Final plan should be one of the values (last one to execute)
        assert subscription_status["plan"] in ["pro", "starter", "enterprise"]
    
    @pytest.mark.asyncio
    async def test_payment_method_deletion_scenario(self):
        """Simulate concurrent payment method deletions."""
        user_id = uuid4()
        payment_methods = {"card1": True, "card2": True, "card3": True}
        deleted_count = 0
        
        async def delete_card(card_id: str):
            nonlocal deleted_count
            async with payment_lock(user_id, "delete_payment_method"):
                if payment_methods.get(card_id):
                    await asyncio.sleep(0.01)  # Simulate Stripe API call
                    payment_methods[card_id] = False
                    deleted_count += 1
        
        # Try to delete same card multiple times concurrently
        await asyncio.gather(
            delete_card("card1"),
            delete_card("card1"),
            delete_card("card1")
        )
        
        # Should only delete once due to locking
        assert deleted_count == 1
        assert payment_methods["card1"] is False
