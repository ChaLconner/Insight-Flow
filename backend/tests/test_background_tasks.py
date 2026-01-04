
import pytest
import asyncio
from unittest.mock import Mock, patch
from utils.background_tasks import (
    fire_and_forget,
    run_in_background,
    background_task,
    run_with_timeout
)

class TestBackgroundTasks:
    """Tests for background task utilities."""

    @pytest.mark.asyncio
    async def test_fire_and_forget_success(self):
        """Test successful execution."""
        mock = Mock()
        
        async def task():
            mock()
            
        fire_and_forget(task())
        
        # Give event loop a moment to run the task
        await asyncio.sleep(0.01)
        
        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_fire_and_forget_exception(self):
        """Test exception handling."""
        async def failing_task():
            raise ValueError("Test error")
            
        # Should not raise exception to caller
        fire_and_forget(failing_task())
        
        await asyncio.sleep(0.01)
        # Verify it didn't crash

    @pytest.mark.asyncio
    async def test_run_in_background(self):
        """Test running blocking function."""
        mock = Mock()
        
        def blocking_func():
            mock()
            
        run_in_background(blocking_func)
        
        await asyncio.sleep(0.05) # Thread overhead
        
        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_background_task_decorator(self):
        """Test decorator usage."""
        mock = Mock()
        
        @background_task
        async def my_bg_task(arg):
            mock(arg)
            
        my_bg_task("hello")
        
        await asyncio.sleep(0.01)
        
        mock.assert_called_with("hello")

    @pytest.mark.asyncio
    async def test_run_with_timeout_success(self):
        """Test success within timeout."""
        async def fast_task():
            return "done"
            
        result = await run_with_timeout(fast_task(), timeout_seconds=1.0)
        assert result == "done"

    @pytest.mark.asyncio
    async def test_run_with_timeout_expired(self):
        """Test timeout expiration."""
        async def slow_task():
            await asyncio.sleep(0.2)
            return "done"
            
        result = await run_with_timeout(slow_task(), timeout_seconds=0.1, default="timeout")
        assert result == "timeout"
