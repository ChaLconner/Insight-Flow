"""
Simple in-app notification service with automatic triggers.
Only creates notifications within the application - no email or push.
Includes rate limiting and notification grouping.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from models.notification import Notification
from models.user import User
from models.user_settings import UserSettings
from services.notification_rate_limiter import get_rate_limiter
from utils.logger import setup_logger

logger = setup_logger("notification_trigger_service")


class NotificationTriggerService:
    """
    Service for triggering in-app notifications.
    Respects user notification preferences.
    Includes rate limiting and grouping features.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.rate_limiter = get_rate_limiter()
    
    def _get_user_preferences(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user notification preferences."""
        try:
            settings = self.db.query(UserSettings).filter(
                UserSettings.user_id == user_id
            ).first()
            
            if settings and settings.notification_preferences:
                return settings.notification_preferences
        except Exception as e:
            logger.warning(f"Failed to get user preferences: {e}")
        
        # Default preferences - all enabled
        return {
            "inApp": {
                "tasks": True,
                "projects": True,
                "mentions": True,
                "updates": True,
                "system": True
            }
        }
    
    def _should_notify(self, preferences: Dict[str, Any], notification_type: str) -> bool:
        """Check if user should receive notification based on preferences."""
        in_app_prefs = preferences.get("inApp", {})
        return in_app_prefs.get(notification_type, True)
    
    def _check_rate_limit(self, user_id: uuid.UUID, notification_type: str) -> bool:
        """Check if notification is allowed by rate limiter."""
        can_send, reason = self.rate_limiter.can_send(str(user_id), notification_type)
        if not can_send:
            logger.info(f"Rate limited notification for user {user_id}: {reason}")
        return can_send
    
    def _find_existing_group_notification(
        self,
        user_id: uuid.UUID,
        notification_type: str,
        group_key: str,
        hours: int = 24
    ) -> Optional[Notification]:
        """
        Find an existing notification that can be grouped with new one.
        Returns the notification if found and still within grouping window.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Look for unread notification of same type within time window
        existing = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.type == notification_type,
            Notification.is_read == False,
            Notification.created_at >= cutoff
        ).first()
        
        return existing
    
    def _update_grouped_notification(
        self,
        notification: Notification,
        new_message: str,
        additional_data: Dict[str, Any]
    ):
        """Update an existing notification with grouped information."""
        try:
            # Get current count or initialize
            current_data = notification.data or {}
            count = current_data.get("count", 1) + 1
            
            # Update the notification
            notification.title = self._get_grouped_title(notification.type, count)
            notification.message = self._get_grouped_message(notification.type, count)
            notification.data = {
                **current_data,
                "count": count,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "items": current_data.get("items", []) + [additional_data]
            }
            # Only keep last 10 items
            notification.data["items"] = notification.data["items"][-10:]
            notification.created_at = datetime.now(timezone.utc)  # Bump to top
            
            self.db.commit()
            logger.info(f"Updated grouped notification for user {notification.user_id}, count: {count}")
        except Exception as e:
            logger.error(f"Failed to update grouped notification: {e}")
            self.db.rollback()
    
    def _get_grouped_title(self, notification_type: str, count: int) -> str:
        """Get title for grouped notification."""
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
        """Get message for grouped notification."""
        messages = {
            "task_assigned": f"You have been assigned {count} new tasks",
            "task_updated": f"{count} tasks have been updated",
            "task_completed": f"{count} tasks have been completed",
            "task_due_soon": f"You have {count} tasks due soon",
            "task_overdue": f"You have {count} overdue tasks - please take action",
            "project_invitation": f"You have been added to {count} projects",
        }
        return messages.get(notification_type, f"You have {count} new notifications")
    
    def _create_notification(
        self,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        allow_grouping: bool = True
    ) -> Optional[Notification]:
        """
        Create an in-app notification in the database.
        Supports rate limiting and optional grouping.
        """
        # Check rate limit
        if not self._check_rate_limit(user_id, notification_type):
            return None
        
        try:
            # Check for groupable notification (only for certain types)
            groupable_types = ["task_due_soon", "task_overdue", "task_updated"]
            
            if allow_grouping and notification_type in groupable_types:
                existing = self._find_existing_group_notification(
                    user_id, notification_type, notification_type
                )
                if existing:
                    self._update_grouped_notification(existing, message, data or {})
                    return existing
            
            # Create new notification
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message,
                data=data or {}
            )
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            
            # Record in rate limiter
            self.rate_limiter.record_notification(str(user_id), notification_type)
            
            logger.info(f"Created notification for user {user_id}: {title}")
            return notification
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            self.db.rollback()
            return None
    
    # ===========================
    # Task Notifications
    # ===========================
    
    async def notify_task_assigned(
        self,
        assignee: User,
        task_id: uuid.UUID,
        task_title: str,
        project_id: uuid.UUID,
        project_name: str,
        assigner: User
    ):
        """Send notification when a task is assigned to someone."""
        # Don't notify if user assigned task to themselves
        if assignee.id == assigner.id:
            return
        
        preferences = self._get_user_preferences(assignee.id)
        
        if self._should_notify(preferences, "tasks"):
            assigner_name = assigner.name or assigner.email.split("@")[0]
            self._create_notification(
                user_id=assignee.id,
                notification_type="task_assigned",
                title="New Task Assigned",
                message=f"{assigner_name} assigned you: {task_title}",
                data={
                    "task_id": str(task_id),
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "assigner_id": str(assigner.id)
                },
                allow_grouping=False  # Each task assignment is important
            )
    
    async def notify_task_status_changed(
        self,
        task_id: uuid.UUID,
        task_title: str,
        project_id: uuid.UUID,
        old_status: str,
        new_status: str,
        changer: User,
        assignee: Optional[User] = None,
        creator: Optional[User] = None
    ):
        """Send notification when task status changes."""
        recipients = []
        
        # Add assignee if exists and not the changer
        if assignee and assignee.id != changer.id:
            recipients.append(assignee)
        
        # Add creator if exists and not already added
        if creator and creator.id != changer.id:
            if not assignee or creator.id != assignee.id:
                recipients.append(creator)
        
        changer_name = changer.name or changer.email.split("@")[0]
        
        for user in recipients:
            preferences = self._get_user_preferences(user.id)
            
            if self._should_notify(preferences, "updates"):
                self._create_notification(
                    user_id=user.id,
                    notification_type="task_updated",
                    title="Task Status Updated",
                    message=f"{changer_name} changed '{task_title}' to {new_status}",
                    data={
                        "task_id": str(task_id),
                        "project_id": str(project_id),
                        "old_status": old_status,
                        "new_status": new_status
                    },
                    allow_grouping=True  # Group multiple updates
                )
    
    async def notify_task_completed(
        self,
        task_id: uuid.UUID,
        task_title: str,
        project_id: uuid.UUID,
        project_name: str,
        completer: User,
        creator: Optional[User] = None
    ):
        """Send notification when a task is completed."""
        if not creator or creator.id == completer.id:
            return
        
        preferences = self._get_user_preferences(creator.id)
        
        if self._should_notify(preferences, "tasks"):
            completer_name = completer.name or completer.email.split("@")[0]
            self._create_notification(
                user_id=creator.id,
                notification_type="task_completed",
                title="Task Completed",
                message=f"{completer_name} completed: {task_title}",
                data={
                    "task_id": str(task_id),
                    "project_id": str(project_id),
                    "project_name": project_name
                },
                allow_grouping=True
            )
    
    def notify_task_due_soon(
        self,
        assignee: User,
        task_id: uuid.UUID,
        task_title: str,
        project_id: uuid.UUID,
        project_name: str,
        due_date: str,
        days_left: int
    ):
        """Send notification when a task is due soon."""
        preferences = self._get_user_preferences(assignee.id)
        
        if self._should_notify(preferences, "tasks"):
            if days_left == 0:
                title = "Task Due Today"
                message = f"'{task_title}' is due today!"
            elif days_left == 1:
                title = "Task Due Tomorrow"
                message = f"'{task_title}' is due tomorrow"
            else:
                title = "Task Due Soon"
                message = f"'{task_title}' is due in {days_left} days"
            
            self._create_notification(
                user_id=assignee.id,
                notification_type="task_due_soon",
                title=title,
                message=message,
                data={
                    "task_id": str(task_id),
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "due_date": due_date,
                    "days_left": days_left
                },
                allow_grouping=True  # Group multiple due soon notifications
            )
    
    def notify_task_overdue(
        self,
        user: User,
        task_id: uuid.UUID,
        task_title: str,
        project_id: uuid.UUID,
        project_name: str,
        due_date: str,
        days_overdue: int
    ):
        """Send notification when a task is overdue."""
        preferences = self._get_user_preferences(user.id)
        
        if self._should_notify(preferences, "tasks"):
            if days_overdue == 1:
                message = f"'{task_title}' was due yesterday"
            else:
                message = f"'{task_title}' is {days_overdue} days overdue"
            
            self._create_notification(
                user_id=user.id,
                notification_type="task_overdue",
                title="Task Overdue",
                message=message,
                data={
                    "task_id": str(task_id),
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "due_date": due_date,
                    "days_overdue": days_overdue
                },
                allow_grouping=True  # Group multiple overdue notifications
            )
    
    # ===========================
    # Project Notifications
    # ===========================
    
    async def notify_project_member_added(
        self,
        new_member: User,
        project_id: uuid.UUID,
        project_name: str,
        role: str,
        inviter: User
    ):
        """Send notification when user is added to a project."""
        # Don't notify if user added themselves
        if new_member.id == inviter.id:
            return
        
        preferences = self._get_user_preferences(new_member.id)
        
        if self._should_notify(preferences, "projects"):
            inviter_name = inviter.name or inviter.email.split("@")[0]
            self._create_notification(
                user_id=new_member.id,
                notification_type="project_invitation",
                title="Added to Project",
                message=f"{inviter_name} added you to {project_name}",
                data={
                    "project_id": str(project_id),
                    "project_name": project_name,
                    "role": role,
                    "inviter_id": str(inviter.id)
                },
                allow_grouping=False  # Each project invitation is important
            )
    
    async def notify_project_member_removed(
        self,
        removed_member: User,
        project_id: uuid.UUID,
        project_name: str,
        remover: User
    ):
        """Send notification when user is removed from a project."""
        # Don't notify if user removed themselves
        if removed_member.id == remover.id:
            return
        
        preferences = self._get_user_preferences(removed_member.id)
        
        if self._should_notify(preferences, "projects"):
            self._create_notification(
                user_id=removed_member.id,
                notification_type="project_member_left",
                title="Removed from Project",
                message=f"You were removed from {project_name}",
                data={
                    "project_id": str(project_id),
                    "project_name": project_name
                },
                allow_grouping=False
            )


def get_notification_trigger_service(db: Session) -> NotificationTriggerService:
    """Factory function to create notification trigger service."""
    return NotificationTriggerService(db)
