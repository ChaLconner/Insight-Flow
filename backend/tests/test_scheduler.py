"""
Tests for services/scheduler.py
"""

import os


class TestSchedulerConfiguration:
    def test_scheduler_skipped_in_test_environment(self):
        """Test that scheduler is skipped in test environment."""
        os.environ["TESTING"] = "true"

        from services.scheduler import shutdown_scheduler, start_scheduler

        # Should return None without starting scheduler
        result = start_scheduler()
        assert result is None

        # Shutdown should not raise
        shutdown_scheduler()

    def test_scheduler_functions_exist(self):
        """Test that scheduler functions are importable."""
        from services.scheduler import (
            get_scheduler,
            shutdown_scheduler,
            start_scheduler,
        )

        assert callable(start_scheduler)
        assert callable(shutdown_scheduler)
        assert callable(get_scheduler)


class TestSchedulerJobs:
    def test_get_scheduler_returns_none_in_test(self):
        """Test get_scheduler returns None in test environment."""
        os.environ["TESTING"] = "true"

        from services.scheduler import get_scheduler

        # In test mode, scheduler should be None or not started
        scheduler = get_scheduler()
        # Either None or a scheduler that's not running
        assert scheduler is None or not getattr(scheduler, "running", True)
