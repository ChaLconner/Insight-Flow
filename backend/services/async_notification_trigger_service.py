"""
Async Notification Trigger Service.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import Notification
from models.user import User
from models.user_settings import UserSettings
from services.notification_rate_limiter import get_rate_limiter
from utils.logger import setup_logger

logger = setup_logger("async_notification_trigger")


class AsyncNotificationTriggerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rate_limiter = get_rate_limiter()

    async def _get_user_preferences(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Get user notification preferences."""
        try:
            res = await self.db.execute(
                select(UserSettings).filter(UserSettings.user_id == user_id)
            )
            settings = res.scalars().first()
            if settings and settings.notification_preferences:
                return settings.notification_preferences
        except Exception as e:
            logger.warning(f"Failed to get user preferences: {e}")

        return {
            "inApp": {
                "tasks": True,
                "projects": True,
                "mentions": True,
                "updates": True,
                "system": True,
            }
        }

    def _should_notify(self, preferences: dict[str, Any], notification_type: str) -> bool:
        in_app_prefs = preferences.get("inApp", {})
        return bool(in_app_prefs.get(notification_type, True))

    def _check_rate_limit(self, user_id: uuid.UUID, notification_type: str) -> bool:
        can_send, reason = self.rate_limiter.can_send(str(user_id), notification_type)
        if not can_send:
            logger.info(f"Rate limited notification for user {user_id}: {reason}")
        return can_send

    async def _find_existing_group_notification(
        self, user_id: uuid.UUID, notification_type: str, hours: int = 24
    ) -> Notification | None:
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        res = await self.db.execute(
            select(Notification).filter(
                Notification.user_id == user_id,
                Notification.type == notification_type,
                Notification.is_read == False,
                Notification.created_at >= cutoff,
            )
        )
        return res.scalars().first()

    async def _update_grouped_notification(
        self, notification: Notification, _message: str, additional_data: dict[str, Any]
    ):
        try:
            current_data = notification.data or {}
            count = current_data.get("count", 1) + 1

            notification.title = self._get_grouped_title(notification.type, count)
            notification.message = self._get_grouped_message(notification.type, count)
            notification.data = {
                **current_data,
                "count": count,
                "last_updated": datetime.now(UTC).isoformat(),
                "items": [*current_data.get("items", []), additional_data][-10:],
            }
            notification.created_at = datetime.now(UTC)

            await self.db.commit()
            logger.info(f"Updated grouped notification for user {notification.user_id}")
        except Exception as e:
            logger.error(f"Failed to update grouped notification: {e}")
            await self.db.rollback()

    def _get_grouped_title(self, notification_type: str, count: int) -> str:
        titles = {
            "task_assigned": f"{count} New Tasks Assigned",
            "task_updated": f"{count} Task Updates",
            "task_completed": f"{count} Tasks Completed",
            "task_due_soon": f"{count} Tasks Due Soon",
            "task_overdue": f"{count} Overdue Tasks",
            "project_invitation": f"Added to {count} Projects",
        }
        return titles.get(notification_type, f"{count} Notifications")

    def _get_grouped_message(self, notification_type: str, count: int) -> str:
        messages = {
            "task_assigned": f"You have been assigned {count} new tasks",
            "task_updated": f"{count} tasks have been updated",
            "task_completed": f"{count} tasks have been completed",
            "task_due_soon": f"You have {count} tasks due soon",
            "task_overdue": f"You have {count} overdue tasks - please take action",
            "project_invitation": f"You have been added to {count} projects",
        }
        return messages.get(notification_type, f"You have {count} new notifications")

    async def _create_notification(
        self,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
        allow_grouping: bool = True,
    ) -> Notification | None:
        if not self._check_rate_limit(user_id, notification_type):
            return None

        try:
            groupable_types = ["task_due_soon", "task_overdue", "task_updated"]
            if allow_grouping and notification_type in groupable_types:
                existing = await self._find_existing_group_notification(user_id, notification_type)
                if existing:
                    await self._update_grouped_notification(existing, message, data or {})
                    return existing

            # Create new
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message,
                data=data or {},
            )
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)

            self.rate_limiter.record_notification(str(user_id), notification_type)
            logger.info(f"Created notification: {title}")
            return notification
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            await self.db.rollback()
            return None

    # Public Async Methods
    async def notify_project_member_added(
        self, new_member: User, project_id: uuid.UUID, project_name: str, role: str, inviter: User
    ):
        if new_member.id == inviter.id:
            return

        prefs = await self._get_user_preferences(new_member.id)
        if self._should_notify(prefs, "projects"):
            inviter_name = inviter.name or inviter.email.split("@")[0]
            await self._create_notification(
                user_id=new_member.id,
                notification_type="project_invitation",
                title="Added to Project",
                message=f"{inviter_name} added you to {project_name}",
                data={
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "role": role,
                    "inviter_id": str(inviter.id),
                },
                allow_grouping=False,
            )

    async def notify_task_assigned(
        self,
        assignee: User,
        task_id: uuid.UUID,
        task_title: str,
        project_id: uuid.UUID,
        project_name: str,
        assigner: User,
    ):
        """Notify user when a task is assigned to them."""
        if assignee.id == assigner.id:
            return  # Don't notify if self-assigning

        prefs = await self._get_user_preferences(assignee.id)
        if self._should_notify(prefs, "tasks"):
            assigner_name = assigner.name or assigner.email.split("@")[0]
            await self._create_notification(
                user_id=assignee.id,
                notification_type="task_assigned",
                title="New Task Assigned",
                message=f"{assigner_name} assigned you a task: {task_title}",
                data={
                    "task_id": str(task_id),
                    "task_title": task_title,
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "assigner_id": str(assigner.id),
                },
                allow_grouping=True,
            )

    async def notify_task_status_changed(
        self,
        task_id: uuid.UUID,
        task_title: str,
        project_id: uuid.UUID,
        old_status: str,
        new_status: str,
        changer: User,
        assignee: User | None = None,
        creator: User | None = None,
    ):
        """Notify relevant users when task status changes."""
        changer_name = changer.name or changer.email.split("@")[0]

        # Notify assignee if they didn't make the change
        if assignee and assignee.id != changer.id:
            prefs = await self._get_user_preferences(assignee.id)
            if self._should_notify(prefs, "tasks"):
                await self._create_notification(
                    user_id=assignee.id,
                    notification_type="task_updated",
                    title="Task Status Changed",
                    message=f"{changer_name} changed '{task_title}' status: {old_status} → {new_status}",
                    data={
                        "task_id": str(task_id),
                        "task_title": task_title,
                        "project_id": str(project_id),
                        "old_status": old_status,
                        "new_status": new_status,
                        "changer_id": str(changer.id),
                    },
                    allow_grouping=True,
                )

        # Notify creator if they didn't make the change and are different from assignee
        if creator and creator.id != changer.id and (not assignee or creator.id != assignee.id):
            prefs = await self._get_user_preferences(creator.id)
            if self._should_notify(prefs, "tasks"):
                await self._create_notification(
                    user_id=creator.id,
                    notification_type="task_updated",
                    title="Task Status Changed",
                    message=f"{changer_name} changed '{task_title}' status: {old_status} → {new_status}",
                    data={
                        "task_id": str(task_id),
                        "task_title": task_title,
                        "project_id": str(project_id),
                        "old_status": old_status,
                        "new_status": new_status,
                        "changer_id": str(changer.id),
                    },
                    allow_grouping=True,
                )

    async def notify_task_completed(
        self,
        task_id: uuid.UUID,
        task_title: str,
        project_id: uuid.UUID,
        project_name: str,
        completer: User,
        creator: User | None = None,
    ):
        """Notify task creator when task is completed."""
        if not creator or creator.id == completer.id:
            return  # Don't notify if the completer is the creator

        prefs = await self._get_user_preferences(creator.id)
        if self._should_notify(prefs, "tasks"):
            completer_name = completer.name or completer.email.split("@")[0]
            await self._create_notification(
                user_id=creator.id,
                notification_type="task_completed",
                title="Task Completed",
                message=f"{completer_name} completed task: {task_title}",
                data={
                    "task_id": str(task_id),
                    "task_title": task_title,
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "completer_id": str(completer.id),
                },
                allow_grouping=True,
            )

    async def notify_task_due_soon(
        self,
        assignee: User,
        task_id: uuid.UUID,
        task_title: str,
        project_id: uuid.UUID,
        project_name: str,
        due_date: str,
        days_left: int,
    ):
        """Notify user about an upcoming task deadline."""
        prefs = await self._get_user_preferences(assignee.id)
        if self._should_notify(prefs, "tasks"):
            message = "is due today" if days_left == 0 else f"is due in {days_left} days"
            await self._create_notification(
                user_id=assignee.id,
                notification_type="task_due_soon",
                title="Task Deadline Approaching",
                message=f"Task '{task_title}' {message} ({due_date})",
                data={
                    "task_id": str(task_id),
                    "task_title": task_title,
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "due_date": due_date,
                    "days_left": days_left,
                },
                allow_grouping=True,
            )

    async def notify_task_overdue(
        self,
        user: User,
        task_id: uuid.UUID,
        task_title: str,
        project_id: uuid.UUID,
        project_name: str,
        due_date: str,
        days_overdue: int,
    ):
        """Notify user about an overdue task."""
        prefs = await self._get_user_preferences(user.id)
        if self._should_notify(prefs, "tasks"):
            await self._create_notification(
                user_id=user.id,
                notification_type="task_overdue",
                title="Task Overdue!",
                message=f"Task '{task_title}' is {days_overdue} days overdue (due was {due_date})",
                data={
                    "task_id": str(task_id),
                    "task_title": task_title,
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "due_date": due_date,
                    "days_overdue": days_overdue,
                },
                allow_grouping=True,
            )
