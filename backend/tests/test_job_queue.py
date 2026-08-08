import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from models.background_job import BackgroundJob, BackgroundJobStatus
from services.job_queue import (
    claim_job,
    cleanup_finished_jobs,
    complete_job,
    enqueue_job,
    fail_job,
    renew_job_lease,
)


@pytest.mark.asyncio
async def test_enqueue_job_is_idempotent(async_session):
    key = f"test:{uuid.uuid4()}"

    first = await enqueue_job(async_session, "test.job", {"value": 1}, idempotency_key=key)
    await async_session.commit()
    second = await enqueue_job(async_session, "test.job", {"value": 2}, idempotency_key=key)

    assert first.id == second.id
    rows = (await async_session.execute(select(BackgroundJob))).scalars().all()
    assert len([row for row in rows if row.idempotency_key == key]) == 1


@pytest.mark.asyncio
async def test_claim_complete_and_retry_job(async_session):
    job = await enqueue_job(async_session, "test.job", {"value": 1})
    await async_session.commit()

    claimed = await claim_job(async_session, "worker-1")
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == BackgroundJobStatus.RUNNING.value
    assert claimed.attempts == 1

    assert await fail_job(async_session, claimed.id, "worker-1", "temporary failure") is True
    stored = await async_session.get(BackgroundJob, claimed.id)
    assert stored is not None
    assert stored.status == BackgroundJobStatus.PENDING.value
    assert stored.last_error == "temporary failure"

    assert await complete_job(async_session, claimed.id, "worker-1") is False


@pytest.mark.asyncio
async def test_claim_reclaims_stale_final_attempt(async_session, monkeypatch):
    monkeypatch.setattr(
        "services.job_queue.get_settings",
        lambda: SimpleNamespace(job_lock_timeout_seconds=60, job_max_attempts=1),
    )
    job = BackgroundJob(
        job_type="test.job",
        payload={"value": 1},
        status=BackgroundJobStatus.RUNNING.value,
        attempts=1,
        locked_at=datetime.now(UTC) - timedelta(minutes=2),
        locked_by="dead-worker",
    )
    async_session.add(job)
    await async_session.commit()

    reclaimed = await claim_job(async_session, "worker-2")

    assert reclaimed is not None
    assert reclaimed.id == job.id
    assert reclaimed.attempts == 1
    assert reclaimed.locked_by == "worker-2"


@pytest.mark.asyncio
async def test_renew_job_lease_updates_only_owned_running_job(async_session):
    await enqueue_job(async_session, "test.job", {"value": 1})
    await async_session.commit()
    claimed = await claim_job(async_session, "worker-1")

    assert claimed is not None
    previous_locked_at = claimed.locked_at
    assert previous_locked_at is not None
    assert await renew_job_lease(async_session, claimed.id, "worker-1") is True
    refreshed = await async_session.get(BackgroundJob, claimed.id)
    assert refreshed is not None
    assert refreshed.locked_at is not None
    assert refreshed.locked_at >= previous_locked_at
    assert await renew_job_lease(async_session, claimed.id, "other-worker") is False


@pytest.mark.asyncio
async def test_cleanup_finished_jobs_removes_only_terminal_old_rows(async_session):
    old = datetime.now(UTC) - timedelta(days=45)
    completed = BackgroundJob(
        job_type="test.completed",
        payload={},
        status=BackgroundJobStatus.COMPLETED.value,
        completed_at=old,
        available_at=old,
    )
    failed = BackgroundJob(
        job_type="test.failed",
        payload={},
        status=BackgroundJobStatus.FAILED.value,
        available_at=old,
    )
    pending = BackgroundJob(
        job_type="test.pending",
        payload={},
        status=BackgroundJobStatus.PENDING.value,
        available_at=old,
    )
    async_session.add_all([completed, failed, pending])
    await async_session.commit()
    completed_id = completed.id
    failed_id = failed.id
    pending_id = pending.id

    assert await cleanup_finished_jobs(async_session, retention_days=30) == 2
    assert await async_session.get(BackgroundJob, completed_id) is None
    assert await async_session.get(BackgroundJob, failed_id) is None
    assert await async_session.get(BackgroundJob, pending_id) is not None
