"""
Background task utilities for fire-and-forget async operations.

This module provides utilities for running non-blocking background tasks
without requiring external dependencies like Celery or RQ.

Usage:
    from utils.background_tasks import fire_and_forget, run_in_background

    # Fire and forget a coroutine
    fire_and_forget(send_email_async(to, subject, body))

    # Run blocking function in background thread
    run_in_background(send_email_sync, to, subject, body)
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

logger = logging.getLogger("background_tasks")

T = TypeVar("T")


def fire_and_forget(coro: Coroutine[Any, Any, T]) -> None:
    """
    Schedule a coroutine to run in the background without awaiting it.
    
    The task runs independently and any exceptions are logged but not raised.
    Use this for non-critical operations like sending emails or notifications.
    
    Args:
        coro: The coroutine to run in the background
        
    Example:
        fire_and_forget(send_notification(user_id, message))
    """
    async def wrapper():
        try:
            await coro
        except Exception as e:
            logger.error(f"Background task failed: {e}", exc_info=True)
    
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(wrapper())
    except RuntimeError:
        # No running loop - run synchronously as fallback
        logger.warning("No running event loop, running task synchronously")
        asyncio.run(wrapper())


def run_in_background(
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any
) -> None:
    """
    Run a blocking function in a background thread without waiting for result.
    
    Use this for blocking I/O operations like SMTP email sending.
    
    Args:
        func: The blocking function to run
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Example:
        run_in_background(send_smtp_email, to, subject, body)
    """
    async def wrapper():
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: func(*args, **kwargs))
        except Exception as e:
            logger.error(f"Background task failed: {e}", exc_info=True)
    
    fire_and_forget(wrapper())


def background_task(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., None]:
    """
    Decorator to make an async function run as a fire-and-forget background task.
    
    Example:
        @background_task
        async def send_notification(user_id: str, message: str):
            # This runs in background, caller doesn't wait
            await notification_service.send(user_id, message)
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        fire_and_forget(func(*args, **kwargs))
    
    return wrapper


async def run_with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout_seconds: float = 30.0,
    default: T | None = None
) -> T | None:
    """
    Run a coroutine with a timeout, returning default value on timeout.
    
    Useful for operations that should have a maximum execution time.
    
    Args:
        coro: The coroutine to run
        timeout_seconds: Maximum time to wait
        default: Value to return on timeout
        
    Returns:
        Result of coroutine or default value on timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(f"Task timed out after {timeout_seconds}s")
        return default
