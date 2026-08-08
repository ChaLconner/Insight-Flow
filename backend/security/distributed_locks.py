"""
Distributed Lock Manager for Payment Operations.

Provides both in-memory and Redis-based locking for concurrent operation prevention.
Redis locks work across multiple workers/processes for horizontal scaling.

Usage:
    # In-memory (single worker)
    async with payment_lock(user_id, "subscription"):
        await update_subscription(...)

    # Redis-based (multi-worker) - set REDIS_URL in environment
    async with payment_lock(user_id, "subscription"):
        await update_subscription(...)
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

from config import get_settings

logger = logging.getLogger("payment.locks")


# ============================================================================
# Abstract Lock Interface
# ============================================================================


class BaseLockManager(ABC):
    """Abstract base class for lock managers."""

    @abstractmethod
    def acquire(
        self, lock_key: str, timeout: float = 30.0, ttl: int = 60
    ) -> AbstractAsyncContextManager[str]:
        """Acquire a lock with timeout and TTL."""
        pass

    @abstractmethod
    async def release(self, lock_key: str, lock_id: str):
        """Release a lock."""
        pass

    @abstractmethod
    async def is_locked(self, lock_key: str) -> bool:
        """Check if a key is currently locked."""
        pass


# ============================================================================
# In-Memory Lock Manager (Single Worker)
# ============================================================================


class InMemoryLockManager(BaseLockManager):
    """
    Simple in-memory lock manager for preventing concurrent payment operations.

    Suitable for single-worker deployments (Gunicorn workers=1).
    For multi-worker deployments, use RedisLockManager.
    """

    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}
        self._lock_owners: dict[str, str] = {}  # key -> lock_id
        self._lock_creation_lock = asyncio.Lock()
        logger.info("Initialized InMemoryLockManager (single-worker mode)")

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create a lock for the given key."""
        if key not in self._locks:
            async with self._lock_creation_lock:
                if key not in self._locks:
                    self._locks[key] = asyncio.Lock()
        return self._locks[key]

    @asynccontextmanager
    async def acquire(self, lock_key: str, timeout: float = 30.0, _ttl: int = 60):
        """
        Acquire a lock for the given key with timeout.

        Args:
            lock_key: Unique identifier for the lock
            timeout: Maximum time to wait for lock (seconds)
            ttl: Lock TTL (not used in memory, included for API compatibility)

        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        lock = await self._get_lock(lock_key)
        lock_id = str(uuid4())

        try:
            # Try to acquire with timeout
            try:
                await asyncio.wait_for(lock.acquire(), timeout=timeout)
            except TimeoutError:
                raise TimeoutError(
                    "Another payment operation is in progress. Please wait and try again."
                )

            self._lock_owners[lock_key] = lock_id
            logger.debug(f"Acquired in-memory lock: {lock_key} ({lock_id})")
            yield lock_id

        finally:
            if lock.locked():
                lock.release()
                self._lock_owners.pop(lock_key, None)
                logger.debug(f"Released in-memory lock: {lock_key}")

    async def release(self, lock_key: str, lock_id: str):
        """Release a lock by key and ID."""
        if lock_key in self._locks:
            lock = self._locks[lock_key]
            if lock.locked() and self._lock_owners.get(lock_key) == lock_id:
                lock.release()
                self._lock_owners.pop(lock_key, None)

    async def is_locked(self, lock_key: str) -> bool:
        """Check if a key is currently locked."""
        if lock_key in self._locks:
            return self._locks[lock_key].locked()
        return False

    def cleanup_old_locks(self):
        """Remove unused locks to prevent memory leaks."""
        unlocked = [k for k, v in self._locks.items() if not v.locked()]
        for key in unlocked:
            del self._locks[key]
            self._lock_owners.pop(key, None)
        if unlocked:
            logger.debug(f"Cleaned up {len(unlocked)} unused locks")


# ============================================================================
# Redis Lock Manager (Multi-Worker)
# ============================================================================


class RedisLockManager(BaseLockManager):
    """
    Redis-based distributed lock manager for multi-worker deployments.

    Uses Redis SET NX with expiration for atomic lock acquisition.
    Implements safe release with Lua script to prevent releasing other's locks.
    """

    # Lua script for safe lock release (only release if we own it)
    RELEASE_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    def __init__(self, redis_url: str, password: str | None = None):
        """
        Initialize Redis lock manager.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
        """
        self._redis_url = redis_url
        self._password = password
        self._redis: Any | None = None
        self._release_script: Any | None = None
        logger.info("Initialized RedisLockManager (multi-worker mode)")

    async def _get_redis(self):
        """Lazy initialization of Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis

                redis_client = aioredis.from_url(
                    self._redis_url,
                    password=self._password,
                    encoding="utf-8",
                    decode_responses=True,
                )
                self._redis = redis_client
                # Register release script
                self._release_script = redis_client.register_script(self.RELEASE_SCRIPT)
                logger.info("Redis connection established for distributed locks")
            except ImportError:
                raise ImportError(
                    "redis package is required for distributed locks. "
                    "Install with: pip install redis"
                )
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._redis

    @asynccontextmanager
    async def acquire(self, lock_key: str, timeout: float = 30.0, ttl: int = 60):
        """
        Acquire a distributed lock with timeout and TTL.

        Args:
            lock_key: Unique identifier for the lock
            timeout: Maximum time to wait for lock (seconds)
            ttl: Lock expiration time (seconds) - prevents deadlocks

        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        redis = await self._get_redis()
        lock_id = str(uuid4())
        full_key = f"payment_lock:{lock_key}"

        start_time = time.time()
        acquired = False

        try:
            # Polling with exponential backoff
            wait_time = 0.1  # Start with 100ms
            while time.time() - start_time < timeout:
                # Try to acquire lock with NX (only if not exists) and EX (expiration)
                acquired = await redis.set(
                    full_key,
                    lock_id,
                    nx=True,  # Only set if not exists
                    ex=ttl,  # Expiration in seconds
                )

                if acquired:
                    logger.debug(f"Acquired Redis lock: {lock_key} ({lock_id})")
                    break

                # Wait before retry (exponential backoff, max 1 second)
                await asyncio.sleep(min(wait_time, 1.0))
                wait_time *= 2

            if not acquired:
                raise TimeoutError(
                    "Another payment operation is in progress. Please wait and try again."
                )

            yield lock_id

        finally:
            if acquired:
                # Safe release using Lua script
                try:
                    if self._release_script:
                        await self._release_script(keys=[full_key], args=[lock_id])
                        logger.debug(f"Released Redis lock: {lock_key}")
                except Exception as e:
                    logger.error(f"Error releasing Redis lock {lock_key}: {e}")

    async def release(self, lock_key: str, lock_id: str):
        """Release a lock by key and ID."""
        await self._get_redis()  # Ensure connection
        full_key = f"payment_lock:{lock_key}"
        try:
            if self._release_script:
                await self._release_script(keys=[full_key], args=[lock_id])
        except Exception as e:
            logger.error(f"Error releasing Redis lock {lock_key}: {e}")

    async def is_locked(self, lock_key: str) -> bool:
        """Check if a key is currently locked."""
        redis = await self._get_redis()
        full_key = f"payment_lock:{lock_key}"
        return bool(await redis.exists(full_key) > 0)

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# ============================================================================
# Lock Manager Factory
# ============================================================================

_lock_manager: BaseLockManager | None = None


def get_lock_manager() -> BaseLockManager:
    """
    Get the appropriate lock manager based on configuration.

    Uses Redis if REDIS_URL is configured,
    otherwise falls back to in-memory locks.
    """
    global _lock_manager

    if _lock_manager is None:
        try:
            cache_settings = get_settings().cache
            redis_url = os.getenv("REDIS_URL") or cache_settings.redis_url
            redis_password = os.getenv("REDIS_PASSWORD") or cache_settings.redis_password
        except Exception:
            redis_url = os.getenv("REDIS_URL")
            redis_password = os.getenv("REDIS_PASSWORD")

        if redis_url:
            try:
                _lock_manager = RedisLockManager(redis_url, password=redis_password)
            except ImportError:
                logger.warning(
                    "Redis package not installed. Falling back to in-memory locks. "
                    "Install with: pip install redis"
                )
                _lock_manager = InMemoryLockManager()
        else:
            _lock_manager = InMemoryLockManager()

    return _lock_manager


def set_lock_manager(manager: BaseLockManager):
    """Set a custom lock manager (useful for testing)."""
    global _lock_manager
    _lock_manager = manager


def reset_lock_manager():
    """Reset the lock manager (useful for testing)."""
    global _lock_manager
    _lock_manager = None


# ============================================================================
# Convenience Functions
# ============================================================================


@asynccontextmanager
async def payment_lock(user_id: UUID, operation: str = "payment", timeout: float = 30.0):
    """
    Convenience function to acquire a user-scoped payment lock.

    Automatically selects Redis or in-memory based on configuration.

    Args:
        user_id: User ID to lock operations for
        operation: Operation type for debugging/namespacing
        timeout: Maximum time to wait for lock

    Usage:
        async with payment_lock(user_id, "subscription"):
            await update_subscription(...)
    """
    lock_key = f"{operation}:{user_id}"
    manager = get_lock_manager()

    async with manager.acquire(lock_key, timeout=timeout):
        yield


@asynccontextmanager
async def resource_lock(resource_type: str, resource_id: str, timeout: float = 30.0):
    """
    Generic resource lock for non-user-specific operations.

    Args:
        resource_type: Type of resource (e.g., "invoice", "subscription")
        resource_id: Unique resource identifier
        timeout: Maximum time to wait for lock
    """
    lock_key = f"{resource_type}:{resource_id}"
    manager = get_lock_manager()

    async with manager.acquire(lock_key, timeout=timeout):
        yield
