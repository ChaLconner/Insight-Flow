"""Postgres-backed queue primitives for durable asynchronous work."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.background_job import BackgroundJob, BackgroundJobStatus
from utils.logger import setup_logger

logger = setup_logger("job_queue")


def _is_postgres(db: AsyncSession) -> bool:
    """Use the production-safe upsert only when the bound engine is PostgreSQL."""
    bind = getattr(db, "bind", None)
    return bool(bind is not None and bind.dialect.name == "postgresql")


async def enqueue_job(
    db: AsyncSession,
    job_type: str,
    payload: dict[str, Any],
    *,
    idempotency_key: str | None = None,
    available_at: datetime | None = None,
) -> BackgroundJob:
    """Stage a job in the caller's transaction.

    The caller owns the commit. This lets domain mutations and their follow-up
    work become visible atomically and prevents a successful HTTP response from
    preceding durable job creation.
    """
    if idempotency_key:
        existing = await db.scalar(
            select(BackgroundJob).where(BackgroundJob.idempotency_key == idempotency_key)
        )
        if existing:
            return existing

    values = {
        "job_type": job_type,
        "payload": payload,
        "idempotency_key": idempotency_key,
        "available_at": available_at or datetime.now(UTC),
    }

    # The pre-check above is an optimization. PostgreSQL must still arbitrate
    # concurrent callers on the unique key, otherwise two requests can both
    # pass the check before either transaction commits.
    if idempotency_key and _is_postgres(db):
        statement = (
            pg_insert(BackgroundJob)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[BackgroundJob.idempotency_key])
            .returning(BackgroundJob.id)
        )
        inserted_id = (await db.execute(statement)).scalar_one_or_none()
        if inserted_id is None:
            existing = await db.scalar(
                select(BackgroundJob).where(BackgroundJob.idempotency_key == idempotency_key)
            )
            if existing:
                return existing
            raise RuntimeError("Idempotent job conflict could not be resolved")
        job = await db.get(BackgroundJob, inserted_id)
        if job is None:
            raise RuntimeError("Inserted background job could not be loaded")
        return job

    job = BackgroundJob(**values)
    db.add(job)
    await db.flush()
    return job


async def cleanup_finished_jobs(
    db: AsyncSession,
    *,
    retention_days: int | None = None,
) -> int:
    """Delete completed and terminally failed jobs past the retention window."""
    settings = get_settings()
    days = retention_days if retention_days is not None else settings.job_retention_days
    if days <= 0:
        raise ValueError("Job retention must be greater than zero days")

    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        delete(BackgroundJob)
        .where(
            or_(
                and_(
                    BackgroundJob.status == BackgroundJobStatus.COMPLETED.value,
                    BackgroundJob.completed_at.is_not(None),
                    BackgroundJob.completed_at < cutoff,
                ),
                and_(
                    BackgroundJob.status == BackgroundJobStatus.FAILED.value,
                    BackgroundJob.available_at < cutoff,
                ),
            )
        )
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return result.rowcount or 0


async def claim_job(
    db: AsyncSession,
    worker_id: str,
    *,
    job_types: set[str] | None = None,
) -> BackgroundJob | None:
    """Atomically claim one available job using row-level locking."""
    settings = get_settings()
    now = datetime.now(UTC)
    stale_before = now - timedelta(seconds=settings.job_lock_timeout_seconds)

    pending_filter = and_(
        BackgroundJob.status == BackgroundJobStatus.PENDING.value,
        BackgroundJob.available_at <= now,
    )
    stale_filter = and_(
        BackgroundJob.status == BackgroundJobStatus.RUNNING.value,
        BackgroundJob.locked_at <= stale_before,
        BackgroundJob.attempts <= settings.job_max_attempts,
    )
    filters = [or_(pending_filter, stale_filter)]
    if job_types:
        filters.append(BackgroundJob.job_type.in_(job_types))

    result = await db.execute(
        select(BackgroundJob)
        .where(*filters)
        .order_by(BackgroundJob.available_at.asc(), BackgroundJob.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = result.scalars().first()
    if job is None:
        await db.rollback()
        return None

    job.status = BackgroundJobStatus.RUNNING.value
    # A worker may crash after claiming the final allowed attempt. Permit one
    # lease reclaim so that job can finish or be marked failed instead of
    # remaining running forever.
    job.attempts = min(job.attempts + 1, settings.job_max_attempts)
    job.locked_at = now
    job.locked_by = worker_id
    job.last_error = None
    await db.commit()
    await db.refresh(job)
    return job


async def complete_job(db: AsyncSession, job_id: uuid.UUID, worker_id: str) -> bool:
    """Mark a job complete only if this worker still owns its lease."""
    result = await db.execute(
        update(BackgroundJob)
        .where(
            BackgroundJob.id == job_id,
            BackgroundJob.status == BackgroundJobStatus.RUNNING.value,
            BackgroundJob.locked_by == worker_id,
        )
        .values(
            status=BackgroundJobStatus.COMPLETED.value,
            completed_at=datetime.now(UTC),
            locked_at=None,
            locked_by=None,
        )
    )
    await db.commit()
    return result.rowcount == 1


async def renew_job_lease(db: AsyncSession, job_id: uuid.UUID, worker_id: str) -> bool:
    """Extend an active lease so long-running handlers are not reclaimed."""
    result = await db.execute(
        update(BackgroundJob)
        .where(
            BackgroundJob.id == job_id,
            BackgroundJob.status == BackgroundJobStatus.RUNNING.value,
            BackgroundJob.locked_by == worker_id,
        )
        .values(locked_at=datetime.now(UTC))
    )
    await db.commit()
    return result.rowcount == 1


async def fail_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    worker_id: str,
    error: str,
) -> bool:
    """Retry a failed job with bounded exponential backoff."""
    settings = get_settings()
    job = await db.scalar(
        select(BackgroundJob).where(
            BackgroundJob.id == job_id,
            BackgroundJob.status == BackgroundJobStatus.RUNNING.value,
            BackgroundJob.locked_by == worker_id,
        )
    )
    if job is None:
        await db.rollback()
        return False

    if job.attempts >= settings.job_max_attempts:
        job.status = BackgroundJobStatus.FAILED.value
        job.available_at = datetime.now(UTC)
    else:
        delay = min(300, 2 ** max(job.attempts - 1, 0))
        job.status = BackgroundJobStatus.PENDING.value
        job.available_at = datetime.now(UTC) + timedelta(seconds=delay)

    job.last_error = error[:4000]
    job.locked_at = None
    job.locked_by = None
    await db.commit()
    return True


async def get_queue_stats(db: AsyncSession) -> dict[str, int]:
    """Return small queue counters for readiness/metrics without payloads."""
    result = await db.execute(
        select(BackgroundJob.status, func.count(BackgroundJob.id)).group_by(BackgroundJob.status)
    )
    counts = dict(result.all())
    return {
        "pending": counts.get(BackgroundJobStatus.PENDING.value, 0),
        "running": counts.get(BackgroundJobStatus.RUNNING.value, 0),
        "completed": counts.get(BackgroundJobStatus.COMPLETED.value, 0),
        "failed": counts.get(BackgroundJobStatus.FAILED.value, 0),
    }
