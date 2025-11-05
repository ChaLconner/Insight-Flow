"""
Service for managing task history and activities.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from models.task_history import TaskHistory, ActivityType
from models.task import Task
from models.user import User
from models.project import Project
import json
import uuid

class TaskHistoryService:
    """Service for task history operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_activity(
        self,
        activity_type: ActivityType,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        task_id: Optional[uuid.UUID] = None,
        task_title: Optional[str] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None
    ) -> TaskHistory:
        """
        Create a new activity record.
        """
        activity = TaskHistory(
            activity_type=activity_type,
            project_id=project_id,
            task_id=task_id,
            user_id=user_id,
            task_title=task_title,
            description=description,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None
        )
        
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity
    
    def get_recent_activities(
        self,
        project_id: uuid.UUID,
        limit: int = 10,
        activity_types: Optional[List[ActivityType]] = None
    ) -> List[TaskHistory]:
        """
        Get recent activities for a project.
        """
        query = self.db.query(TaskHistory).filter(TaskHistory.project_id == project_id)
        
        if activity_types:
            query = query.filter(TaskHistory.activity_type.in_(activity_types))
        
        return query.order_by(TaskHistory.timestamp.desc()).limit(limit).all()
    
    def get_task_activities(self, task_id: uuid.UUID) -> List[TaskHistory]:
        """
        Get all activities for a specific task.
        """
        return self.db.query(TaskHistory).filter(
            TaskHistory.task_id == task_id
        ).order_by(TaskHistory.timestamp.desc()).all()
    
    def get_user_activities(
        self,
        user_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> List[TaskHistory]:
        """
        Get activities performed by a specific user.
        """
        query = self.db.query(TaskHistory).filter(TaskHistory.user_id == user_id)
        
        if project_id:
            query = query.filter(TaskHistory.project_id == project_id)
        
        return query.order_by(TaskHistory.timestamp.desc()).limit(limit).all()
    
    def log_task_created(self, task: Task, creator_id: uuid.UUID) -> TaskHistory:
        """
        Log task creation activity.
        """
        return self.create_activity(
            activity_type=ActivityType.TASK_CREATED,
            project_id=task.project_id,
            user_id=creator_id,
            task_id=task.id,
            task_title=task.title,
            description=f"Created task: {task.title}",
            new_values={
                "title": task.title,
                "description": task.description,
                "status": task.status.value if task.status else None,
                "assignee_id": str(task.assignee_id) if task.assignee_id else None,
                "due_date": task.due_date.isoformat() if task.due_date else None
            }
        )
    
    def log_task_updated(
        self,
        task: Task,
        user_id: uuid.UUID,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any]
    ) -> TaskHistory:
        """
        Log task update activity.
        """
        return self.create_activity(
            activity_type=ActivityType.TASK_UPDATED,
            project_id=task.project_id,
            user_id=user_id,
            task_id=task.id,
            task_title=task.title,
            description=f"Updated task: {task.title}",
            old_values=old_values,
            new_values=new_values
        )
    
    def log_task_completed(self, task: Task, user_id: uuid.UUID) -> TaskHistory:
        """
        Log task completion activity.
        """
        return self.create_activity(
            activity_type=ActivityType.TASK_COMPLETED,
            project_id=task.project_id,
            user_id=user_id,
            task_id=task.id,
            task_title=task.title,
            description=f"Completed task: {task.title}",
            new_values={"status": "done"}
        )
    
    def log_task_assigned(self, task: Task, assignee_id: uuid.UUID, assigned_by: uuid.UUID) -> TaskHistory:
        """
        Log task assignment activity.
        """
        # Get assignee user info
        assignee = self.db.query(User).filter(User.id == assignee_id).first()
        assignee_name = assignee.name if assignee else "Unknown User"
        
        return self.create_activity(
            activity_type=ActivityType.TASK_ASSIGNED,
            project_id=task.project_id,
            user_id=assigned_by,
            task_id=task.id,
            task_title=task.title,
            description=f"Assigned task '{task.title}' to {assignee_name}",
            new_values={"assignee_id": str(assignee_id), "assignee_name": assignee_name}
        )
    
    def log_task_unassigned(self, task: Task, unassigned_by: uuid.UUID) -> TaskHistory:
        """
        Log task unassignment activity.
        """
        return self.create_activity(
            activity_type=ActivityType.TASK_UNASSIGNED,
            project_id=task.project_id,
            user_id=unassigned_by,
            task_id=task.id,
            task_title=task.title,
            description=f"Unassigned task: {task.title}",
            old_values={"assignee_id": str(task.assignee_id)} if task.assignee_id else None
        )
    
    def log_task_deleted(self, task: Task, deleted_by: uuid.UUID) -> TaskHistory:
        """
        Log task deletion activity.
        """
        return self.create_activity(
            activity_type=ActivityType.TASK_DELETED,
            project_id=task.project_id,
            user_id=deleted_by,
            task_id=task.id,
            task_title=task.title,
            description=f"Deleted task: {task.title}",
            old_values={
                "title": task.title,
                "description": task.description,
                "status": task.status.value if task.status else None
            }
        )