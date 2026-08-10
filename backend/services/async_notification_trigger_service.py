"""
Async Notification Trigger Service.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from html import escape
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.background_job import BackgroundJob
from models.notification import Notification
from models.user import User
from models.user_settings import UserSettings
from services.email_service import EmailService
from services.job_queue import enqueue_job
from services.notification_rate_limiter import get_rate_limiter
from utils.logger import setup_logger

logger = setup_logger("async_notification_trigger")
EMAIL_JOB_TYPE = "email.send"


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
            await self.db.rollback()
            raise

        return {
            "inApp": {
                "tasks": True,
                "projects": True,
                "mentions": True,
                "updates": True,
                "system": True,
            },
            "email": {
                "tasks": True,
                "projects": True,
                "mentions": True,
            },
        }

    def _should_notify(
        self, preferences: dict[str, Any], channel: str, notification_type: str
    ) -> bool:
        channel_prefs = preferences.get(channel, {})
        return bool(channel_prefs.get(notification_type, True))

    def _should_notify_in_app(self, preferences: dict[str, Any], notification_type: str) -> bool:
        in_app_prefs = preferences.get("inApp", {})
        return bool(in_app_prefs.get(notification_type, True))

    def _should_notify_email(self, preferences: dict[str, Any], notification_type: str) -> bool:
        email_prefs = preferences.get("email", {})
        return bool(email_prefs.get(notification_type, False))

    async def _send_email_notification(
        self,
        user: User,
        email_type: str,
        subject: str,
        message: str,
        action_path: str | None = None,
    ) -> None:
        prefs = await self._get_user_preferences(user.id)
        if not self._should_notify_email(prefs, email_type):
            return
        if not await self._check_email_rate_limit(user, email_type):
            return

        try:
            import os

            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
            action_url = f"{frontend_url}{action_path}" if action_path else frontend_url
            # Notification fields include task, project, comment, and actor
            # text supplied by users. Keep the email template HTML-capable,
            # but escape this untrusted text before placing it in the body.
            content = f"<p>{escape(message)}</p>"
            html_email = EmailService._get_base_template(
                subject, content, action_url, "Open Insight Flow"
            )
            idempotency_key = (
                "notification-email:"
                + hashlib.sha256(f"{user.id}:{subject}:{message}".encode()).hexdigest()
            )
            await enqueue_job(
                self.db,
                EMAIL_JOB_TYPE,
                {
                    "method": "send_email",
                    "to_email": user.email,
                    "subject": f"Insight Flow - {subject}",
                    "html_content": html_email,
                },
                idempotency_key=idempotency_key,
            )
            self.rate_limiter.record_notification(f"email:{user.id}", email_type)
            logger.info("Queued notification email for user %s", user.id)
        except Exception as e:
            logger.warning(f"Failed to queue notification email to user {user.id}: {e}")
            await self.db.rollback()
            # The caller is a durable notification job. Propagate the queue
            # failure so the worker can retry instead of silently losing mail.
            raise

    def _check_rate_limit(self, user_id: uuid.UUID, notification_type: str) -> bool:
        can_send, reason = self.rate_limiter.can_send(str(user_id), notification_type)
        if not can_send:
            logger.info(f"Rate limited notification for user {user_id}: {reason}")
        return can_send

    async def _check_email_rate_limit(self, user: User, email_type: str) -> bool:
        """Bound outbound email fan-out separately from in-app notices."""
        key = f"email:{user.id}"
        allowed, reason = self.rate_limiter.can_send(key, email_type)
        if not allowed:
            logger.info("Rate limited email notification for %s: %s", user.id, reason)
            return False

        cutoff = datetime.now(UTC) - timedelta(hours=1)
        try:
            result = await self.db.execute(
                select(func.count(BackgroundJob.id)).where(
                    BackgroundJob.job_type == EMAIL_JOB_TYPE,
                    BackgroundJob.created_at >= cutoff,
                    BackgroundJob.payload["to_email"].as_string() == user.email,
                )
            )
            count = result.scalar_one()
            if isinstance(count, int) and count >= self.rate_limiter.max_per_hour:
                logger.info("Durable email rate limit reached for %s", user.id)
                return False
        except Exception as exc:
            logger.warning("Email rate-limit lookup failed: %s", exc)
            return False
        return True

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

            logger.info(f"Updated grouped notification for user {notification.user_id}")
        except Exception as e:
            logger.error(f"Failed to update grouped notification: {e}")
            await self.db.rollback()
            raise

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
            await self.db.flush()
            await self.db.refresh(notification)

            self.rate_limiter.record_notification(str(user_id), notification_type)
            logger.info(f"Created notification: {title}")
            return notification
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            await self.db.rollback()
            raise

    # Public Async Methods
    async def notify_project_member_added(
        self, new_member: User, project_id: uuid.UUID, project_name: str, role: str, inviter: User
    ):
        if new_member.id == inviter.id:
            return

        prefs = await self._get_user_preferences(new_member.id)
        inviter_name = inviter.name or inviter.email.split("@")[0]
        message = f"{inviter_name} added you to {project_name}"
        if self._should_notify_in_app(prefs, "projects"):
            await self._create_notification(
                user_id=new_member.id,
                notification_type="project_invitation",
                title="Added to Project",
                message=message,
                data={
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "role": role,
                    "inviter_id": str(inviter.id),
                },
                allow_grouping=False,
            )
        await self._send_email_notification(
            new_member, "projects", "Added to Project", message, f"/projects/{project_id}"
        )

    async def notify_project_member_removed(
        self, removed_member: User, project_id: uuid.UUID, project_name: str, remover: User
    ):
        if removed_member.id == remover.id:
            return

        prefs = await self._get_user_preferences(removed_member.id)
        remover_name = remover.name or remover.email.split("@")[0]
        message = f"{remover_name} removed you from {project_name}"
        if self._should_notify_in_app(prefs, "projects"):
            await self._create_notification(
                user_id=removed_member.id,
                notification_type="project_member_left",
                title="Removed from Project",
                message=message,
                data={
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "remover_id": str(remover.id),
                },
                allow_grouping=False,
            )
        await self._send_email_notification(
            removed_member, "projects", "Removed from Project", message, None
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
        assigner_name = assigner.name or assigner.email.split("@")[0]
        message = f"{assigner_name} assigned you a task: {task_title}"
        if self._should_notify_in_app(prefs, "tasks"):
            await self._create_notification(
                user_id=assignee.id,
                notification_type="task_assigned",
                title="New Task Assigned",
                message=message,
                data={
                    "task_id": str(task_id),
                    "task_title": task_title,
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "assigner_id": str(assigner.id),
                },
                allow_grouping=True,
            )
        await self._send_email_notification(
            assignee,
            "tasks",
            "New Task Assigned",
            message,
            f"/projects/{project_id}?task={task_id}",
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
            message = f"{changer_name} changed '{task_title}' status: {old_status} → {new_status}"
            if self._should_notify_in_app(prefs, "updates"):
                await self._create_notification(
                    user_id=assignee.id,
                    notification_type="task_updated",
                    title="Task Status Changed",
                    message=message,
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
            await self._send_email_notification(
                assignee,
                "tasks",
                "Task Status Changed",
                message,
                f"/projects/{project_id}?task={task_id}",
            )

        # Notify creator if they didn't make the change and are different from assignee
        if creator and creator.id != changer.id and (not assignee or creator.id != assignee.id):
            prefs = await self._get_user_preferences(creator.id)
            message = f"{changer_name} changed '{task_title}' status: {old_status} → {new_status}"
            if self._should_notify_in_app(prefs, "updates"):
                await self._create_notification(
                    user_id=creator.id,
                    notification_type="task_updated",
                    title="Task Status Changed",
                    message=message,
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
            await self._send_email_notification(
                creator,
                "tasks",
                "Task Status Changed",
                message,
                f"/projects/{project_id}?task={task_id}",
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
        completer_name = completer.name or completer.email.split("@")[0]
        message = f"{completer_name} completed task: {task_title}"
        if self._should_notify_in_app(prefs, "tasks"):
            await self._create_notification(
                user_id=creator.id,
                notification_type="task_completed",
                title="Task Completed",
                message=message,
                data={
                    "task_id": str(task_id),
                    "task_title": task_title,
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "completer_id": str(completer.id),
                },
                allow_grouping=True,
            )
        await self._send_email_notification(
            creator, "tasks", "Task Completed", message, f"/projects/{project_id}?task={task_id}"
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
        due_message = "is due today" if days_left == 0 else f"is due in {days_left} days"
        message = f"Task '{task_title}' {due_message} ({due_date})"
        if self._should_notify_in_app(prefs, "tasks"):
            await self._create_notification(
                user_id=assignee.id,
                notification_type="task_due_soon",
                title="Task Deadline Approaching",
                message=message,
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
        await self._send_email_notification(
            assignee,
            "tasks",
            "Task Deadline Approaching",
            message,
            f"/projects/{project_id}?task={task_id}",
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
        message = f"Task '{task_title}' is {days_overdue} days overdue (due was {due_date})"
        if self._should_notify_in_app(prefs, "tasks"):
            await self._create_notification(
                user_id=user.id,
                notification_type="task_overdue",
                title="Task Overdue!",
                message=message,
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
        await self._send_email_notification(
            user, "tasks", "Task Overdue!", message, f"/projects/{project_id}?task={task_id}"
        )

    async def notify_mention(
        self,
        mentioned_user: User,
        actor: User,
        message: str,
        project_id: uuid.UUID | None = None,
        task_id: uuid.UUID | None = None,
    ):
        """Notify user when mentioned in a comment or update."""
        if mentioned_user.id == actor.id:
            return

        prefs = await self._get_user_preferences(mentioned_user.id)
        actor_name = actor.name or actor.email.split("@")[0]
        notification_message = f"{actor_name} mentioned you: {message}"
        action_path = (
            f"/projects/{project_id}?task={task_id}"
            if project_id and task_id
            else f"/projects/{project_id}"
            if project_id
            else None
        )
        if self._should_notify_in_app(prefs, "mentions"):
            await self._create_notification(
                user_id=mentioned_user.id,
                notification_type="mention",
                title="You were mentioned",
                message=notification_message,
                data={
                    "project_id": str(project_id) if project_id else None,
                    "task_id": str(task_id) if task_id else None,
                    "actor_id": str(actor.id),
                },
                allow_grouping=False,
            )
        await self._send_email_notification(
            mentioned_user, "mentions", "You were mentioned", notification_message, action_path
        )
