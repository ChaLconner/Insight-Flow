"""
Payment operation utilities for idempotency and concurrency control.
Provides idempotency key generation and distributed locking for payment operations.

Note: Lock functionality has been moved to distributed_locks.py for better
multi-worker support. The payment_lock function is re-exported from there
for backward compatibility.
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any
from uuid import UUID

from stripe import (
    APIConnectionError,
    AuthenticationError,
    CardError,
    InvalidRequestError,
    RateLimitError,
)

# Re-export payment_lock and get_lock_manager from distributed_locks for backward compatibility
from security.distributed_locks import get_lock_manager, payment_lock  # noqa: F401

logger = logging.getLogger("payment.utils")


# ============================================================================
# Idempotency Key Generation
# ============================================================================


def generate_idempotency_key(
    operation: str,
    user_id: UUID,
    *args: Any,
    ttl_seconds: int = 86400,  # 24 hours default
) -> str:
    """
    Generate a unique idempotency key for Stripe operations.

    The key is deterministic based on operation + user + args, so retrying
    the same operation with the same parameters will use the same key.

    Args:
        operation: Type of operation (e.g., "create_subscription", "add_payment_method")
        user_id: User performing the operation
        *args: Additional unique identifiers (e.g., plan_id, amount)
        ttl_seconds: Time window for idempotency (default 24h)

    Returns:
        A unique idempotency key string

    Example:
        key = generate_idempotency_key("create_subscription", user_id, "pro")
        # Returns: "sub_create_subscription_<hash>_<time_bucket>"
    """
    # Create time bucket to allow same operation after TTL
    time_bucket = int(time.time() / ttl_seconds)

    # Combine all unique identifiers
    unique_parts = [
        operation,
        str(user_id),
        *[str(arg) for arg in args if arg is not None],
        str(time_bucket),
    ]

    # Create deterministic hash
    content = ":".join(unique_parts)
    hash_digest = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Prefix for easy identification in Stripe dashboard
    prefix = operation[:10].replace("_", "")

    return f"idk_{prefix}_{hash_digest}"


def generate_setup_intent_key(user_id: UUID) -> str:
    """Generate idempotency key for SetupIntent creation."""
    return generate_idempotency_key("setup_intent", user_id, ttl_seconds=300)  # 5 min


def generate_subscription_key(user_id: UUID, plan: str) -> str:
    """Generate idempotency key for subscription creation/update."""
    return generate_idempotency_key("subscription", user_id, plan)


def generate_payment_method_key(user_id: UUID, payment_method_id: str) -> str:
    """Generate idempotency key for payment method attachment."""
    return generate_idempotency_key("attach_pm", user_id, payment_method_id, ttl_seconds=60)


def generate_customer_key(user_id: UUID, email: str) -> str:
    """Generate idempotency key for customer creation."""
    return generate_idempotency_key("customer", user_id, email)


# ============================================================================
# NOTE: Lock Manager moved to distributed_locks.py
# ============================================================================
# The PaymentLockManager class and payment_lock function have been moved to
# security/distributed_locks.py for better multi-worker support (Redis).
# They are re-exported at the top of this file for backward compatibility.
#


# ============================================================================
# Retry Decorator for Transient Failures
# ============================================================================


def retry_on_stripe_error(
    max_retries: int = 3, retry_delay: float = 1.0, exponential_backoff: bool = True
):
    """
    Decorator to retry Stripe operations on transient failures.

    Retries on:
    - RateLimitError
    - APIConnectionError
    - Some InvalidRequestErrors (resource temporarily unavailable)

    Does NOT retry on:
    - CardError (card declined, invalid, etc.)
    - AuthenticationError (API key issues)
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error: Any = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)

                except RateLimitError as e:
                    last_error = e
                    logger.warning(f"Rate limit hit, attempt {attempt + 1}/{max_retries}")

                except APIConnectionError as e:
                    last_error = e
                    logger.warning(f"Connection error, attempt {attempt + 1}/{max_retries}")

                except InvalidRequestError as e:
                    # Only retry if it's a temporary issue
                    if "temporarily" in str(e).lower() or "try again" in str(e).lower():
                        last_error = e
                        logger.warning(f"Temporary error, attempt {attempt + 1}/{max_retries}")
                    else:
                        raise

                except (CardError, AuthenticationError):
                    # Don't retry these
                    raise

                # Wait before retry
                if attempt < max_retries - 1:
                    delay = retry_delay * (2**attempt if exponential_backoff else 1)
                    await asyncio.sleep(delay)

            # All retries exhausted
            if last_error:
                raise last_error

        return wrapper

    return decorator
