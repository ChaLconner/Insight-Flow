"""
Background scheduler for running periodic tasks.
Uses APScheduler to run deadline checks and other maintenance tasks.
Refactored to use async services.
"""

from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import AsyncSessionLocal
from services.async_deadline_reminder import run_async_deadline_check
from utils.logger import setup_logger

logger = setup_logger("scheduler")

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler


async def run_deadline_check_job():
    """
    Async job function for deadline check.
    Creates its own database session.
    """
    logger.info("Running scheduled deadline check...")

    async with AsyncSessionLocal() as db:
        try:
            summary = await run_async_deadline_check(db)
            logger.info(f"Deadline check completed: {summary}")
        except Exception as e:
            logger.error(f"Deadline check failed: {e}")


def setup_scheduled_jobs(sched: AsyncIOScheduler):
    """Configure all scheduled jobs."""

    # Deadline check - runs every day at 8:00 AM (server time)
    sched.add_job(
        run_deadline_check_job,
        CronTrigger(hour=8, minute=0),
        id="deadline_check_morning",
        name="Morning Deadline Check",
        replace_existing=True,
    )

    # Optional: Run a second check at 2:00 PM for afternoon reminder
    sched.add_job(
        run_deadline_check_job,
        CronTrigger(hour=14, minute=0),
        id="deadline_check_afternoon",
        name="Afternoon Deadline Check",
        replace_existing=True,
    )

    logger.info("Scheduled jobs configured:")
    logger.info("  - Deadline check: 8:00 AM and 2:00 PM daily")


def start_scheduler():
    """Start the background scheduler."""
    global scheduler

    # Skip scheduler in test environment
    import os

    if os.environ.get("TESTING") == "true":
        logger.info("Scheduler skipped in test environment")
        return None

    try:
        scheduler = get_scheduler()

        if not scheduler.running:
            setup_scheduled_jobs(scheduler)
            scheduler.start()
            logger.info("Background scheduler started")

        return scheduler
    except RuntimeError as e:
        # Handle event loop issues
        if "Event loop is closed" in str(e) or "no running event loop" in str(e):
            logger.warning(f"Could not start scheduler: {e}")
            return None
        raise


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    global scheduler

    # Skip in test environment
    import os

    if os.environ.get("TESTING") == "true":
        return

    try:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Background scheduler stopped")
    except RuntimeError as e:
        # Handle event loop issues during shutdown
        if "Event loop is closed" in str(e) or "no running event loop" in str(e):
            logger.debug(f"Scheduler shutdown skipped: {e}")
        else:
            logger.error(f"Error shutting down scheduler: {e}")


@asynccontextmanager
async def lifespan_scheduler(app):
    """
    Lifespan context manager for FastAPI.
    Use this in main.py: app = FastAPI(lifespan=lifespan_scheduler)
    """
    start_scheduler()
    yield
    shutdown_scheduler()
