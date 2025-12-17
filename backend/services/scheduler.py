"""
Background scheduler for running periodic tasks.
Uses APScheduler to run deadline checks and other maintenance tasks.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager
from typing import Optional

from database import SessionLocal
from services.deadline_reminder import run_deadline_check
from utils.logger import setup_logger

logger = setup_logger("scheduler")

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler


def run_deadline_check_job():
    """
    Job function for deadline check.
    Creates its own database session.
    """
    logger.info("Running scheduled deadline check...")
    
    db = SessionLocal()
    try:
        summary = run_deadline_check(db)
        logger.info(f"Deadline check completed: {summary}")
    except Exception as e:
        logger.error(f"Deadline check failed: {e}")
    finally:
        db.close()


def setup_scheduled_jobs(sched: AsyncIOScheduler):
    """Configure all scheduled jobs."""
    
    # Deadline check - runs every day at 8:00 AM (server time)
    sched.add_job(
        run_deadline_check_job,
        CronTrigger(hour=8, minute=0),
        id="deadline_check_morning",
        name="Morning Deadline Check",
        replace_existing=True
    )
    
    # Optional: Run a second check at 2:00 PM for afternoon reminder
    sched.add_job(
        run_deadline_check_job,
        CronTrigger(hour=14, minute=0),
        id="deadline_check_afternoon",
        name="Afternoon Deadline Check",
        replace_existing=True
    )
    
    logger.info("Scheduled jobs configured:")
    logger.info("  - Deadline check: 8:00 AM and 2:00 PM daily")


def start_scheduler():
    """Start the background scheduler."""
    global scheduler
    scheduler = get_scheduler()
    
    if not scheduler.running:
        setup_scheduled_jobs(scheduler)
        scheduler.start()
        logger.info("Background scheduler started")
    
    return scheduler


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")


@asynccontextmanager
async def lifespan_scheduler(app):
    """
    Lifespan context manager for FastAPI.
    Use this in main.py: app = FastAPI(lifespan=lifespan_scheduler)
    """
    start_scheduler()
    yield
    shutdown_scheduler()
