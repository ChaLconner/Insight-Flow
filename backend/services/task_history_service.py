"""
Service for managing task history and activities.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from models.task_history import TaskHistory, ActivityType
from models.task import Task
from models.user import User
from models.project import Project
from utils.logger import setup_logger
import json
import uuid

logger = setup_logger("task_history_service")

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
        logger.debug(f"Creating activity: {activity_type}, project_id: {project_id}, user_id: {user_id}")
        
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
        logger.debug("Activity added to database session")
        
        try:
            self.db.commit()
            logger.debug("Activity committed to database")
            
            self.db.refresh(activity)
            logger.debug(f"Activity refreshed with ID: {activity.id}")
            return activity
        except Exception as e:
            logger.error(f"Error during activity creation: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            self.db.rollback()
            raise ValueError(f"Failed to create activity: {str(e)}")
    
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
        
    def get_recent_activities_for_projects(
        self,
        project_ids: List[uuid.UUID],
        limit: int = 20,
        activity_types: Optional[List[ActivityType]] = None
    ) -> List[TaskHistory]:
        """
        Get recent activities across multiple projects.
        """
        if not project_ids:
            return []
            
        query = self.db.query(TaskHistory).filter(TaskHistory.project_id.in_(project_ids))
        
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
                "status": task.status.value if hasattr(task.status, 'value') else str(task.status) if task.status else None,
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
        # Ensure status in new_values/old_values is serializable if present
        if new_values and 'status' in new_values:
            status_val = new_values['status']
            if hasattr(status_val, 'value'):
                new_values['status'] = status_val.value
        
        if old_values and 'status' in old_values:
            status_val = old_values['status']
            if hasattr(status_val, 'value'):
                old_values['status'] = status_val.value

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
        status_val = task.status.value if hasattr(task.status, 'value') else str(task.status)
        return self.create_activity(
            activity_type=ActivityType.TASK_COMPLETED,
            project_id=task.project_id,
            user_id=user_id,
            task_id=task.id,
            task_title=task.title,
            description=f"Completed task: {task.title}",
            new_values={"status": status_val if task.status else None}
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
        status_val = task.status.value if hasattr(task.status, 'value') else str(task.status)
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
                "status": status_val if task.status else None
            }
        )
    def log_project_member_added(self, project_id: uuid.UUID, member_name: str, added_by: uuid.UUID) -> TaskHistory:
        """
        Log project member addition activity.
        """
        return self.create_activity(
            activity_type=ActivityType.PROJECT_MEMBER_ADDED,
            project_id=project_id,
            user_id=added_by,
            description=f"Added {member_name} to project",
            new_values={"member_name": member_name}
        )
    
    def log_project_member_removed(self, project_id: uuid.UUID, member_name: str, removed_by: uuid.UUID) -> TaskHistory:
        """
        Log project member removal activity.
        """
        return self.create_activity(
            activity_type=ActivityType.PROJECT_MEMBER_REMOVED,
            project_id=project_id,
            user_id=removed_by,
            description=f"Removed {member_name} from project",
            old_values={"member_name": member_name}
        )
    
    def log_project_member_role_changed(self, project_id: uuid.UUID, member_name: str, new_role: str, changed_by: uuid.UUID) -> TaskHistory:
        """
        Log project member role change activity.
        """
        return self.create_activity(
            activity_type=ActivityType.PROJECT_MEMBER_ROLE_CHANGED,
            project_id=project_id,
            user_id=changed_by,
            description=f"Changed {member_name}'s role to {new_role}",
            new_values={"member_name": member_name, "new_role": new_role}
        )
    
    def log_project_updated(self, project_id: uuid.UUID, updated_by: uuid.UUID, changes: Dict[str, Any]) -> TaskHistory:
        """
        Log project update activity.
        """
        return self.create_activity(
            activity_type=ActivityType.PROJECT_UPDATED,
            project_id=project_id,
            user_id=updated_by,
            description="Updated project information",
            new_values=changes
        )
    
    def log_project_created(self, project_id: uuid.UUID, project_name: str, created_by: uuid.UUID) -> TaskHistory:
        """
        Log project creation activity.
        """
        return self.create_activity(
            activity_type=ActivityType.PROJECT_CREATED,
            project_id=project_id,
            user_id=created_by,
            description=f"Created project: {project_name}",
            new_values={"project_name": project_name, "action": "created"}
        )

# Standalone function for background tasks
def log_activity_background(
    activity_type_str: str,
    project_id_str: str,
    user_id_str: str,
    task_id_str: Optional[str] = None,
    task_title: Optional[str] = None,
    description: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None
):
    """
    Background task wrapper for logging activity.
    Handles its own database session.
    """
    from database import get_db_context
    from models.task_history import ActivityType
    
    # Reconstruct UUIDs
    try:
        project_id = uuid.UUID(project_id_str)
        user_id = uuid.UUID(user_id_str)
        task_id = uuid.UUID(task_id_str) if task_id_str else None
        
        # Convert string back to enum
        activity_type = ActivityType(activity_type_str)
        
        with get_db_context() as db:
            service = TaskHistoryService(db)
            service.create_activity(
                activity_type=activity_type,
                project_id=project_id,
                user_id=user_id,
                task_id=task_id,
                task_title=task_title,
                description=description,
                old_values=old_values,
                new_values=new_values
            )
    except Exception as e:
        logger.error(f"Failed to execute background activity log: {e}")