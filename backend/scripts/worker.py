"""Run the durable background-job worker and its single scheduler owner."""

import asyncio
import signal
import socket
import time
import uuid
from contextlib import suppress

from config import get_settings
from database import AsyncSessionLocal, async_engine
from models.background_job import BackgroundJob
from services.email_service import EmailService
from services.job_handlers import handle_job
from services.job_queue import (
    claim_job,
    cleanup_finished_jobs,
    complete_job,
    fail_job,
    renew_job_lease,
)
from services.scheduler import shutdown_scheduler, start_scheduler
from utils.logger import setup_logger

logger = setup_logger("worker")


async def _renew_lease_until_stopped(
    job_id: uuid.UUID,
    worker_id: str,
    stop_event: asyncio.Event,
    lease_lost: asyncio.Event,
    interval: float,
) -> None:
    """Keep a claimed job lease alive while its handler performs work."""
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            continue
        except TimeoutError:
            pass

        try:
            async with AsyncSessionLocal() as db:
                if not await renew_job_lease(db, job_id, worker_id):
                    lease_lost.set()
                    logger.warning("Lost lease for background job %s", job_id)
                    return
        except Exception as exc:
            logger.warning("Failed to renew lease for background job %s: %s", job_id, exc)


async def _cleanup_finished_jobs_if_due(last_cleanup_at: float, interval: float) -> float:
    """Run terminal-job retention cleanup at most once per interval."""
    if time.monotonic() - last_cleanup_at < interval:
        return last_cleanup_at

    async with AsyncSessionLocal() as cleanup_db:
        removed = await cleanup_finished_jobs(cleanup_db)
    if removed:
        logger.info("Removed %s expired background jobs", removed)
    return time.monotonic()


async def _claim_next_job(worker_id: str) -> BackgroundJob | None:
    """Claim one job, keeping transient database errors inside the poll loop."""
    try:
        async with AsyncSessionLocal() as db:
            return await claim_job(db, worker_id)
    except Exception as exc:
        logger.error("Failed to claim background job: %s", exc)
        return None


async def _stop_lease_renewal(lease_stop: asyncio.Event, lease_task: asyncio.Task[None]) -> None:
    """Stop and await a lease-renewal task without leaking cancellation errors."""
    lease_stop.set()
    lease_task.cancel()
    with suppress(asyncio.CancelledError):
        await lease_task


async def _process_job(job: BackgroundJob, worker_id: str) -> None:
    """Execute one claimed job and record its terminal state."""
    lease_stop = asyncio.Event()
    lease_lost = asyncio.Event()
    lease_interval = max(1.0, get_settings().job_lock_timeout_seconds / 3)
    lease_task = asyncio.create_task(
        _renew_lease_until_stopped(
            job.id,
            worker_id,
            lease_stop,
            lease_lost,
            lease_interval,
        )
    )
    try:
        async with AsyncSessionLocal() as db:
            try:
                await handle_job(db, job.job_type, job.payload)
                if lease_lost.is_set():
                    raise RuntimeError("Background job lease lost before commit")
                await db.commit()
            except Exception:
                await db.rollback()
                raise

        await _stop_lease_renewal(lease_stop, lease_task)
        async with AsyncSessionLocal() as db:
            completed = await complete_job(db, job.id, worker_id)
        if not completed:
            logger.warning(
                "Background job %s completed its handler but no longer owned its lease",
                job.id,
            )
        logger.info("Completed background job %s (%s)", job.id, job.job_type)
    except Exception as exc:
        await _stop_lease_renewal(lease_stop, lease_task)
        logger.error("Background job %s (%s) failed: %s", job.id, job.job_type, exc)
        try:
            async with AsyncSessionLocal() as db:
                await fail_job(db, job.id, worker_id, str(exc))
        except Exception as fail_exc:
            logger.error("Failed to record background job failure: %s", fail_exc)


async def run_worker(stop_event: asyncio.Event) -> None:
    """Claim and execute jobs until shutdown is requested."""
    settings = get_settings()
    worker_id = f"{socket.gethostname()}:{uuid.uuid4().hex[:12]}"
    logger.info("Durable worker started: %s", worker_id)
    last_cleanup_at = 0.0
    cleanup_interval = 3600.0

    while not stop_event.is_set():
        job = None
        try:
            last_cleanup_at = await _cleanup_finished_jobs_if_due(last_cleanup_at, cleanup_interval)
            job = await _claim_next_job(worker_id)
        except Exception as exc:
            logger.error("Failed during worker poll: %s", exc)

        if job is None:
            with suppress(TimeoutError):
                await asyncio.wait_for(
                    stop_event.wait(), timeout=settings.job_poll_interval_seconds
                )
            continue

        await _process_job(job, worker_id)

    logger.info("Durable worker stopped: %s", worker_id)


async def main() -> None:
    """Start one scheduler owner and one durable worker loop."""
    settings = get_settings()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError, RuntimeError):
            loop.add_signal_handler(signal_name, stop_event.set)

    scheduler_started = settings.scheduler_enabled
    if scheduler_started:
        start_scheduler()
    else:
        logger.info("Background scheduler disabled for worker")
    try:
        await run_worker(stop_event)
    finally:
        if scheduler_started:
            shutdown_scheduler()
        await EmailService.close()
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
