"""
Deadline reminder scheduler for checking due and overdue tasks.
Runs periodically to send notifications about upcoming and overdue tasks.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from models.task import Task, TaskStatus
from models.user import User
from models.notification import Notification
from services.notification_trigger_service import NotificationTriggerService
from utils.logger import setup_logger

logger = setup_logger("deadline_reminder")


class DeadlineReminderService:
    """Service for checking and notifying about task deadlines."""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationTriggerService(db)
    
    def check_deadlines(self) -> dict:
        """
        Check all tasks for upcoming and overdue deadlines.
        Returns summary of notifications sent.
        """
        now = datetime.now(timezone.utc)
        today = now.date()
        
        summary = {
            "due_today": 0,
            "due_tomorrow": 0,
            "due_in_3_days": 0,
            "overdue": 0,
            "total_notifications": 0
        }
        
        # Get all active tasks with due dates that are not completed
        tasks = self.db.query(Task).options(
            joinedload(Task.assignee),
            joinedload(Task.creator),
            joinedload(Task.project)
        ).filter(
            Task.due_date.isnot(None),
            Task.status != TaskStatus.DONE
        ).all()
        
        for task in tasks:
            if not task.due_date:
                continue
            
            # Handle both date and datetime
            if hasattr(task.due_date, 'date'):
                due_date = task.due_date.date()
            else:
                due_date = task.due_date
            
            days_until_due = (due_date - today).days
            
            # Skip if no assignee
            if not task.assignee:
                continue
            
            # Check if we already sent a notification today for this task
            if self._already_notified_today(task.assignee.id, task.id, days_until_due):
                continue
            
            project_name = task.project.name if task.project else "Unknown Project"
            due_date_str = due_date.isoformat()
            
            if days_until_due < 0:
                # Task is overdue
                days_overdue = abs(days_until_due)
                self.notification_service.notify_task_overdue(
                    user=task.assignee,
                    task_id=task.id,
                    task_title=task.title,
                    project_id=task.project_id,
                    project_name=project_name,
                    due_date=due_date_str,
                    days_overdue=days_overdue
                )
                summary["overdue"] += 1
                summary["total_notifications"] += 1
                
                # Also notify creator if different from assignee
                if task.creator and task.creator.id != task.assignee.id:
                    if not self._already_notified_today(task.creator.id, task.id, days_until_due):
                        self.notification_service.notify_task_overdue(
                            user=task.creator,
                            task_id=task.id,
                            task_title=task.title,
                            project_id=task.project_id,
                            project_name=project_name,
                            due_date=due_date_str,
                            days_overdue=days_overdue
                        )
                        summary["total_notifications"] += 1
                        
            elif days_until_due == 0:
                # Due today
                self.notification_service.notify_task_due_soon(
                    assignee=task.assignee,
                    task_id=task.id,
                    task_title=task.title,
                    project_id=task.project_id,
                    project_name=project_name,
                    due_date=due_date_str,
                    days_left=0
                )
                summary["due_today"] += 1
                summary["total_notifications"] += 1
                
            elif days_until_due == 1:
                # Due tomorrow
                self.notification_service.notify_task_due_soon(
                    assignee=task.assignee,
                    task_id=task.id,
                    task_title=task.title,
                    project_id=task.project_id,
                    project_name=project_name,
                    due_date=due_date_str,
                    days_left=1
                )
                summary["due_tomorrow"] += 1
                summary["total_notifications"] += 1
                
            elif days_until_due <= 3:
                # Due in 2-3 days
                self.notification_service.notify_task_due_soon(
                    assignee=task.assignee,
                    task_id=task.id,
                    task_title=task.title,
                    project_id=task.project_id,
                    project_name=project_name,
                    due_date=due_date_str,
                    days_left=days_until_due
                )
                summary["due_in_3_days"] += 1
                summary["total_notifications"] += 1
        
        logger.info(f"Deadline check complete: {summary}")
        return summary
    
    def _already_notified_today(
        self, 
        user_id, 
        task_id, 
        days_until_due: int
    ) -> bool:
        """Check if we already sent a deadline notification today for this task."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        # Determine notification type based on days
        if days_until_due < 0:
            notif_type = "task_overdue"
        else:
            notif_type = "task_due_soon"
        
        existing = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.type == notif_type,
            Notification.created_at >= today_start,
            Notification.data["task_id"].astext == str(task_id)
        ).first()
        
        return existing is not None


def run_deadline_check(db: Session) -> dict:
    """
    Run deadline check - can be called from scheduler or API endpoint.
    """
    service = DeadlineReminderService(db)
    return service.check_deadlines()
