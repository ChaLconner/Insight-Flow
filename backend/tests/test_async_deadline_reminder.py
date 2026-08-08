import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import services.async_deadline_reminder as deadline_module
from services.async_deadline_reminder import AsyncDeadlineReminderService


def _task_result(tasks):
    result = MagicMock()
    result.scalars.return_value.all.return_value = tasks
    return result


def _notification_result(rows):
    result = MagicMock()
    result.all.return_value = rows
    return result


def _task(*, due_date, assignee_id=None):
    task_id = uuid.uuid4()
    assignee = SimpleNamespace(id=assignee_id) if assignee_id else None
    return SimpleNamespace(
        id=task_id,
        due_date=due_date,
        assignee=assignee,
        creator=None,
        project=SimpleNamespace(name="Project"),
        project_id=uuid.uuid4(),
        title="Task",
    )


@pytest.mark.asyncio
async def test_check_deadlines_processes_bounded_batches(monkeypatch):
    monkeypatch.setattr(deadline_module, "TASK_BATCH_SIZE", 1)
    assignee_id = uuid.uuid4()
    today = datetime.now(UTC).date()
    first = _task(due_date=today, assignee_id=assignee_id)
    second = _task(due_date=today, assignee_id=assignee_id)

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _task_result([first]),
            _notification_result([]),
            _task_result([second]),
            _notification_result([]),
            _task_result([]),
        ]
    )
    service = AsyncDeadlineReminderService(db)
    service.notification_service.notify_task_due_soon = AsyncMock()

    summary = await service.check_deadlines()

    assert summary["due_today"] == 2
    assert summary["total_notifications"] == 2
    assert service.notification_service.notify_task_due_soon.await_count == 2
    assert db.execute.await_count == 5


@pytest.mark.asyncio
async def test_check_deadlines_skips_existing_notification():
    assignee_id = uuid.uuid4()
    task = _task(due_date=datetime.now(UTC).date(), assignee_id=assignee_id)

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            _task_result([task]),
            _notification_result([(assignee_id, "task_due_soon", str(task.id))]),
            _task_result([]),
        ]
    )
    service = AsyncDeadlineReminderService(db)
    service.notification_service.notify_task_due_soon = AsyncMock()

    summary = await service.check_deadlines()

    assert summary["total_notifications"] == 0
    service.notification_service.notify_task_due_soon.assert_not_awaited()
