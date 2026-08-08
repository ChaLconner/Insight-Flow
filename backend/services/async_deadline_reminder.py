"""
Async Deadline reminder service for checking due and overdue tasks.
Runs periodically to send notifications about upcoming and overdue tasks.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.notification import Notification
from models.task import Task, TaskStatus
from services.async_notification_trigger_service import AsyncNotificationTriggerService
from utils.logger import setup_logger

logger = setup_logger("async_deadline_reminder")
TASK_BATCH_SIZE = 250


class AsyncDeadlineReminderService:
    """Async service for checking and notifying about task deadlines."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_service = AsyncNotificationTriggerService(db)

    async def check_deadlines(self) -> dict[str, int]:
        """
        Check all tasks for upcoming and overdue deadlines.
        Returns summary of notifications sent.
        """
        now = datetime.now(UTC)
        today = now.date()

        summary = {
            "due_today": 0,
            "due_tomorrow": 0,
            "due_in_3_days": 0,
            "overdue": 0,
            "total_notifications": 0,
        }

        # Process stable ID-ordered pages so large task tables do not occupy
        # the worker's memory or transaction all at once.
        last_task_id: uuid.UUID | None = None
        while True:
            tasks = await self._get_task_batch(last_task_id)
            if not tasks:
                break

            notified_keys = await self._get_notified_keys(tasks, now)
            await self._process_task_batch(tasks, today, notified_keys, summary)
            last_task_id = tasks[-1].id

        logger.info(f"Deadline check complete: {summary}")
        return summary

    async def _get_task_batch(self, last_task_id: uuid.UUID | None) -> list[Task]:
        """Load one stable page of active tasks with due dates."""
        query = (
            select(Task)
            .options(
                selectinload(Task.assignee), selectinload(Task.creator), selectinload(Task.project)
            )
            .filter(Task.due_date.isnot(None), Task.status != TaskStatus.DONE)
        )
        if last_task_id is not None:
            query = query.filter(Task.id > last_task_id)
        query = query.order_by(Task.id.asc()).limit(TASK_BATCH_SIZE)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _process_task_batch(
        self,
        tasks: list[Task],
        today,
        notified_keys: set[tuple[Any, Any, str]],
        summary: dict[str, int],
    ) -> None:
        """Evaluate one task page and queue its due-date notifications."""
        for task in tasks:
            if not task.due_date:
                continue

            # Handle both date and datetime
            due_date = task.due_date.date() if hasattr(task.due_date, "date") else task.due_date

            days_until_due = (due_date - today).days

            # Skip if no assignee
            if not task.assignee:
                continue

            # Check if we already sent a notification today for this task
            notification_type = "task_overdue" if days_until_due < 0 else "task_due_soon"
            if (task.assignee.id, task.id, notification_type) in notified_keys:
                continue

            project_name = task.project.name if task.project else "Unknown Project"
            due_date_str = due_date.isoformat()

            if days_until_due < 0:
                # Task is overdue
                days_overdue = abs(days_until_due)
                await self.notification_service.notify_task_overdue(
                    user=task.assignee,
                    task_id=task.id,
                    task_title=task.title,
                    project_id=task.project_id,
                    project_name=project_name,
                    due_date=due_date_str,
                    days_overdue=days_overdue,
                )
                summary["overdue"] += 1
                summary["total_notifications"] += 1

                # Also notify creator if different from assignee
                if (
                    task.creator
                    and task.creator.id != task.assignee.id
                    and (
                        task.creator.id,
                        task.id,
                        notification_type,
                    )
                    not in notified_keys
                ):
                    await self.notification_service.notify_task_overdue(
                        user=task.creator,
                        task_id=task.id,
                        task_title=task.title,
                        project_id=task.project_id,
                        project_name=project_name,
                        due_date=due_date_str,
                        days_overdue=days_overdue,
                    )
                    summary["total_notifications"] += 1

            elif days_until_due == 0:
                # Due today
                await self.notification_service.notify_task_due_soon(
                    assignee=task.assignee,
                    task_id=task.id,
                    task_title=task.title,
                    project_id=task.project_id,
                    project_name=project_name,
                    due_date=due_date_str,
                    days_left=0,
                )
                summary["due_today"] += 1
                summary["total_notifications"] += 1

            elif days_until_due == 1:
                # Due tomorrow
                await self.notification_service.notify_task_due_soon(
                    assignee=task.assignee,
                    task_id=task.id,
                    task_title=task.title,
                    project_id=task.project_id,
                    project_name=project_name,
                    due_date=due_date_str,
                    days_left=1,
                )
                summary["due_tomorrow"] += 1
                summary["total_notifications"] += 1

            elif days_until_due <= 3:
                # Due in 2-3 days
                await self.notification_service.notify_task_due_soon(
                    assignee=task.assignee,
                    task_id=task.id,
                    task_title=task.title,
                    project_id=task.project_id,
                    project_name=project_name,
                    due_date=due_date_str,
                    days_left=days_until_due,
                )
                summary["due_in_3_days"] += 1
                summary["total_notifications"] += 1

    async def _get_notified_keys(
        self, tasks: list[Task], now: datetime
    ) -> set[tuple[Any, Any, str]]:
        """Load today's deadline notifications in one query instead of N+1 checks."""
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        task_ids = {str(task.id) for task in tasks}
        user_ids = {
            user_id
            for task in tasks
            for user_id in (
                task.assignee.id if task.assignee else None,
                task.creator.id if task.creator else None,
            )
            if user_id is not None
        }
        if not task_ids or not user_ids:
            return set()

        task_id_value = Notification.data["task_id"].as_string()
        query = select(
            Notification.user_id,
            Notification.type,
            task_id_value,
        ).filter(
            Notification.user_id.in_(user_ids),
            Notification.type.in_(["task_due_soon", "task_overdue"]),
            Notification.created_at >= today_start,
            task_id_value.in_(task_ids),
        )
        result = await self.db.execute(query)
        notified_keys: set[tuple[Any, Any, str]] = set()
        for user_id, notification_type, task_id in result.all():
            if not task_id:
                continue
            try:
                notified_keys.add((user_id, uuid.UUID(str(task_id)), notification_type))
            except ValueError:
                logger.warning("Ignoring malformed task ID in notification %s", task_id)
        return notified_keys


async def run_async_deadline_check(db: AsyncSession) -> dict:
    """
    Run deadline check asynchronously - can be called from scheduler or API endpoint.
    """
    service = AsyncDeadlineReminderService(db)
    return await service.check_deadlines()
