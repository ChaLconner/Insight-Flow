"""
Tests for security/payment_operations.py

Tests payment operation utilities like idempotency keys and locks.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4


class TestIdempotencyKeyGeneration:
    """Tests for idempotency key generation functions."""
    
    def test_generate_setup_intent_key(self):
        """Test generating setup intent idempotency key."""
        from security.payment_operations import generate_setup_intent_key
        
        user_id = uuid4()
        key = generate_setup_intent_key(user_id)
        
        assert key is not None
        assert len(key) > 0
        assert isinstance(key, str)
    
    def test_generate_subscription_key(self):
        """Test generating subscription idempotency key."""
        from security.payment_operations import generate_subscription_key
        
        user_id = uuid4()
        plan = "pro"
        key = generate_subscription_key(user_id, plan)
        
        assert key is not None
        assert len(key) > 0
        assert isinstance(key, str)
    
    def test_different_users_different_keys(self):
        """Test different users get different keys."""
        from security.payment_operations import generate_setup_intent_key
        
        user1_id = uuid4()
        user2_id = uuid4()
        
        key1 = generate_setup_intent_key(user1_id)
        key2 = generate_setup_intent_key(user2_id)
        
        # Keys should be different for different users
        assert key1 != key2


class TestPaymentLock:
    """Tests for payment lock context manager."""
    
    @pytest.mark.asyncio
    async def test_payment_lock_acquires_and_releases(self):
        """Test payment lock is acquired and released."""
        from security.payment_operations import payment_lock
        
        user_id = uuid4()
        operation = "setup_intent"
        
        # Should not raise
        async with payment_lock(user_id, operation):
            pass  # Lock should be held here
    
    @pytest.mark.asyncio
    async def test_payment_lock_with_different_operations(self):
        """Test payment locks for different operations."""
        from security.payment_operations import payment_lock
        
        user_id = uuid4()
        
        # Different operations should not block each other
        async with payment_lock(user_id, "setup_intent"):
            pass
        
        async with payment_lock(user_id, "subscription"):
            pass
