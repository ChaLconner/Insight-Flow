"""
Task service layer for task management.
"""
from typing import Optional, List, Dict, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc
from models.task import Task, TaskStatus, TaskPriority, TaskType
from models.project import Project, ProjectMember, MemberRole
from models.user import User
from schemas.task import TaskCreate, TaskUpdate, TaskStatusUpdate, TaskAssign
from .task_history_service import TaskHistoryService
from utils.logger import logger
import uuid

class TaskService:
    """Service class for task operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_history_service = TaskHistoryService(db)
    
    def get_task_by_id(self, task_id: uuid.UUID) -> Optional[Task]:
        """Get task by ID."""
        return self.db.query(Task).filter(Task.id == task_id).first()
    
    def get_tasks(self, skip: int = 0, limit: int = 100, project_id: Optional[uuid.UUID] = None,
                assignee_id: Optional[uuid.UUID] = None, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get tasks with pagination and optional filters."""
        from sqlalchemy.orm import joinedload
        
        query = self.db.query(Task).options(
            joinedload(Task.assignee),
            joinedload(Task.creator),
            joinedload(Task.project)
        )
        
        if project_id:
            query = query.filter(Task.project_id == project_id)
        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)
        if status:
            query = query.filter(Task.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    def create_task(self, task_data: TaskCreate, created_by: uuid.UUID) -> Task:
        """Create a new task."""
        logger.info(f"Creating task with data: {task_data}, created_by: {created_by}")
        
        # Check if project exists and user is a member
        project = self.db.query(Project).filter(Project.id == task_data.project_id).first()
        if not project:
            raise ValueError("Project not found")
        
        # Check if assignee exists (if provided)
        if task_data.assignee_id:
            assignee = self.db.query(User).filter(User.id == task_data.assignee_id).first()
            if not assignee:
                raise ValueError("Assignee not found")
        
        try:
            # Handle status
            task_status = TaskStatus.TODO
            if task_data.status:
                try:
                    status_lower = task_data.status.lower()
                    if status_lower in [s.value for s in TaskStatus]:
                        task_status = TaskStatus(status_lower)
                except ValueError:
                    pass
            
            # Handle priority
            task_priority = TaskPriority.MEDIUM
            if task_data.priority:
                try:
                    priority_lower = task_data.priority.lower()
                    if priority_lower in [p.value for p in TaskPriority]:
                        task_priority = TaskPriority(priority_lower)
                except ValueError:
                    pass

            # Handle type
            task_type = TaskType.FEATURE
            if task_data.type:
                try:
                    type_lower = task_data.type.lower()
                    if type_lower in [t.value for t in TaskType]:
                        task_type = TaskType(type_lower)
                except ValueError:
                    pass

            db_task = Task(
                title=task_data.title,
                description=task_data.description,
                status=task_status,
                priority=task_priority,
                type=task_type,
                project_id=task_data.project_id,
                assignee_id=task_data.assignee_id,
                created_by=created_by,
                due_date=task_data.due_date
            )
            
            self.db.add(db_task)
            self.db.commit()
            self.db.refresh(db_task)
            
            # Log activities
            self.task_history_service.log_task_created(db_task, created_by)
            if task_data.assignee_id:
                self.task_history_service.log_task_assigned(db_task, task_data.assignee_id, created_by)
            
            return db_task
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Task creation failed")
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Task creation failed: {str(e)}")
    
    def update_task(self, task_id: uuid.UUID, task_data: TaskUpdate, user_id: uuid.UUID) -> Task:
        """Update task information."""
        task = self.get_task_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check permissions: Creator, Assignee, or Project Admin/Owner
        is_authorized = False
        if task.created_by == user_id or task.assignee_id == user_id:
            is_authorized = True
        else:
            member = self.db.query(ProjectMember).filter(
                ProjectMember.project_id == task.project_id,
                ProjectMember.user_id == user_id
            ).first()
            if member and member.role in [MemberRole.OWNER.value, MemberRole.ADMIN.value]:
                is_authorized = True
        
        if not is_authorized:
            raise ValueError("Not authorized to update this task")
        
        # Check if assignee exists (if provided)
        if task_data.assignee_id:
            assignee = self.db.query(User).filter(User.id == task_data.assignee_id).first()
            if not assignee:
                raise ValueError("Assignee not found")
        
        old_values = {}
        new_values = {}
        old_assignee_id = task.assignee_id
        
        # Update fields
        if task_data.title is not None and task_data.title != task.title:
            old_values["title"] = task.title
            new_values["title"] = task_data.title
            task.title = task_data.title
            
        if task_data.description is not None and task_data.description != task.description:
            old_values["description"] = task.description
            new_values["description"] = task_data.description
            task.description = task_data.description
            
        if task_data.status is not None:
            try:
                status_lower = task_data.status.lower()
                if status_lower in [s.value for s in TaskStatus]:
                    new_status = TaskStatus(status_lower)
                    if new_status != task.status:
                        old_values["status"] = task.status.value
                        new_values["status"] = new_status.value
                        task.status = new_status
            except ValueError:
                pass

        if task_data.priority is not None:
            try:
                priority_lower = task_data.priority.lower()
                if priority_lower in [p.value for p in TaskPriority]:
                    new_priority = TaskPriority(priority_lower)
                    if new_priority != task.priority:
                        old_values["priority"] = task.priority.value
                        new_values["priority"] = new_priority.value
                        task.priority = new_priority
            except ValueError:
                pass

        if task_data.type is not None:
            try:
                type_lower = task_data.type.lower()
                if type_lower in [t.value for t in TaskType]:
                    new_type = TaskType(type_lower)
                    if new_type != task.type:
                        old_values["type"] = task.type.value
                        new_values["type"] = new_type.value
                        task.type = new_type
            except ValueError:
                pass
                
        if task_data.assignee_id is not None and task_data.assignee_id != task.assignee_id:
            task.assignee_id = task_data.assignee_id
            if old_assignee_id:
                old_values["assignee_id"] = str(old_assignee_id)
                self.task_history_service.log_task_unassigned(task, user_id)
            new_values["assignee_id"] = str(task_data.assignee_id)
            
        if task_data.due_date is not None and task_data.due_date != task.due_date:
            old_values["due_date"] = task.due_date.isoformat() if task.due_date else None
            new_values["due_date"] = task_data.due_date.isoformat() if task_data.due_date else None
            task.due_date = task_data.due_date
        
        try:
            self.db.commit()
            self.db.refresh(task)
            
            if old_values or new_values:
                self.task_history_service.log_task_updated(task, user_id, old_values, new_values)
            
            if task_data.assignee_id and task_data.assignee_id != old_assignee_id:
                self.task_history_service.log_task_assigned(task, task_data.assignee_id, user_id)
            
            if task_data.status and task_data.status.lower() == 'done' and task.status == TaskStatus.DONE:
                self.task_history_service.log_task_completed(task, user_id)
            
            return task
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Task update failed")
    
    def delete_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a task."""
        task = self.get_task_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check permissions: Creator or Project Admin/Owner
        is_authorized = False
        if task.created_by == user_id:
            is_authorized = True
        else:
            member = self.db.query(ProjectMember).filter(
                ProjectMember.project_id == task.project_id,
                ProjectMember.user_id == user_id
            ).first()
            if member and member.role in [MemberRole.OWNER.value, MemberRole.ADMIN.value]:
                is_authorized = True
        
        if not is_authorized:
            raise ValueError("Not authorized to delete this task")
        
        self.task_history_service.log_task_deleted(task, user_id)
            
        try:
            self.db.delete(task)
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Task deletion failed")
    
    def update_task_status(self, task_id: uuid.UUID, status_update: TaskStatusUpdate, user_id: uuid.UUID) -> Task:
        """Update task status."""
        task = self.get_task_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check permissions: Creator, Assignee, or Project Admin/Owner
        is_authorized = False
        if task.created_by == user_id or task.assignee_id == user_id:
            is_authorized = True
        else:
            member = self.db.query(ProjectMember).filter(
                ProjectMember.project_id == task.project_id,
                ProjectMember.user_id == user_id
            ).first()
            if member and member.role in [MemberRole.OWNER.value, MemberRole.ADMIN.value]:
                is_authorized = True
        
        if not is_authorized:
            raise ValueError("Not authorized to update task status")
        
        old_status = task.status
        
        try:
            status_lower = status_update.status.lower()
            if status_lower in [s.value for s in TaskStatus]:
                task.status = TaskStatus(status_lower)
            else:
                raise ValueError("Invalid task status")
                
            self.db.commit()
            self.db.refresh(task)
            
            if old_status != task.status:
                if task.status == TaskStatus.DONE:
                    self.task_history_service.log_task_completed(task, user_id)
                else:
                    self.task_history_service.log_task_updated(task, user_id, 
                        {"status": old_status.value},
                        {"status": task.status.value})
            
            return task
        except ValueError as e:
            raise e
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Task status update failed")
    
    def assign_task(self, task_id: uuid.UUID, assign_data: TaskAssign, user_id: uuid.UUID) -> Task:
        """Assign task to a user."""
        task = self.get_task_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check permissions: Creator or Project Admin/Owner
        is_authorized = False
        if task.created_by == user_id:
            is_authorized = True
        else:
            member = self.db.query(ProjectMember).filter(
                ProjectMember.project_id == task.project_id,
                ProjectMember.user_id == user_id
            ).first()
            if member and member.role in [MemberRole.OWNER.value, MemberRole.ADMIN.value]:
                is_authorized = True
        
        if not is_authorized:
            raise ValueError("Not authorized to assign task")
        
        assignee = self.db.query(User).filter(User.id == assign_data.assignee_id).first()
        if not assignee:
            raise ValueError("Assignee not found")
        
        try:
            task.assignee_id = assign_data.assignee_id
            self.db.commit()
            self.db.refresh(task)
            
            self.task_history_service.log_task_assigned(task, assign_data.assignee_id, user_id)
            
            return task
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Task assignment failed")
    
    
    def get_user_tasks(
        self, 
        user_id: uuid.UUID, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Task]:
        """
        Get tasks assigned to or created by a user with optional filtering.
        """
        from sqlalchemy import or_
        
        query = self.db.query(Task).filter(
            or_(Task.assignee_id == user_id, Task.created_by == user_id)
        )
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Task.title.ilike(search_term),
                    Task.description.ilike(search_term)
                )
            )
            
        # Apply status filter
        if status and status.lower() != 'all':
            try:
                # Handle status enum matching
                status_lower = status.lower()
                query = query.filter(Task.status == status_lower)
            except Exception:
                # If exact enum match fails (e.g. if we store as string in db but enum in model)
                # Fallback to string comparison if needed, though Task.status should be compatible
                pass
                
        # Order by updated_at desc (most recent first)
        query = query.order_by(desc(Task.updated_at))
        
        return query.offset(skip).limit(limit).all()
    
    def get_project_tasks(
        self, 
        project_id: uuid.UUID, 
        skip: int = 0, 
        limit: int = 100, 
        sort_by: Optional[str] = None, 
        sort_order: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Task]:
        """
        Get tasks for a specific project with optional sorting and filtering.
        """
        from sqlalchemy.orm import joinedload
        from sqlalchemy import or_
        
        query = self.db.query(Task).options(
            joinedload(Task.assignee),
            joinedload(Task.creator),
            joinedload(Task.project)
        ).filter(Task.project_id == project_id)
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Task.title.ilike(search_term),
                    Task.description.ilike(search_term)
                )
            )
            
        # Apply status filter
        if status and status.lower() != 'all':
            try:
                status_lower = status.lower()
                query = query.filter(Task.status == status_lower)
            except Exception:
                pass
        
        if sort_by:
            sort_field_map = {
                'created_at': Task.created_at,
                'updated_at': Task.updated_at,
                'title': Task.title,
                'due_date': Task.due_date,
                'status': Task.status,
                'priority': Task.priority,
                'type': Task.type
            }
            
            if sort_by in sort_field_map:
                sort_field = sort_field_map[sort_by]
                if sort_order and sort_order.lower() == 'desc':
                    query = query.order_by(desc(sort_field))
                else:
                    query = query.order_by(asc(sort_field))
        else:
            # Default sort
            query = query.order_by(desc(Task.updated_at))
        
        return query.offset(skip).limit(limit).all()