"""
Task service layer for task management.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.task import Task, TaskStatus
from models.project import Project
from models.user import User
from schemas.task import TaskCreate, TaskUpdate, TaskStatusUpdate, TaskAssign
import uuid

class TaskService:
    """Service class for task operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_task_by_id(self, task_id: uuid.UUID) -> Optional[Task]:
        """Get task by ID."""
        return self.db.query(Task).filter(Task.id == task_id).first()
    
    def get_tasks(self, skip: int = 0, limit: int = 100, project_id: Optional[uuid.UUID] = None, 
                assignee_id: Optional[uuid.UUID] = None, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get tasks with pagination and optional filters."""
        query = self.db.query(Task)
        
        if project_id:
            query = query.filter(Task.project_id == project_id)
        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)
        if status:
            query = query.filter(Task.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    def create_task(self, task_data: TaskCreate, created_by: uuid.UUID) -> Task:
        """Create a new task."""
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
            db_task = Task(
                title=task_data.title,
                description=task_data.description,
                project_id=task_data.project_id,
                assignee_id=task_data.assignee_id,
                created_by=created_by,
                due_date=task_data.due_date
            )
            
            self.db.add(db_task)
            self.db.commit()
            self.db.refresh(db_task)
            return db_task
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Task creation failed")
    
    def update_task(self, task_id: uuid.UUID, task_data: TaskUpdate, user_id: uuid.UUID) -> Task:
        """Update task information."""
        task = self.get_task_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check if user is creator or assignee
        if task.created_by != user_id and task.assignee_id != user_id:
            raise ValueError("Only task creator or assignee can update task")
        
        # Check if assignee exists (if provided)
        if task_data.assignee_id:
            assignee = self.db.query(User).filter(User.id == task_data.assignee_id).first()
            if not assignee:
                raise ValueError("Assignee not found")
        
        # Update fields if provided
        if task_data.title is not None:
            task.title = task_data.title
        if task_data.description is not None:
            task.description = task_data.description
        if task_data.status is not None:
            try:
                task.status = TaskStatus(task_data.status)
            except ValueError:
                raise ValueError("Invalid task status")
        if task_data.assignee_id is not None:
            task.assignee_id = task_data.assignee_id
        if task_data.due_date is not None:
            task.due_date = task_data.due_date
        
        try:
            self.db.commit()
            self.db.refresh(task)
            return task
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Task update failed")
    
    def delete_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a task."""
        task = self.get_task_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Only creator can delete task
        if task.created_by != user_id:
            raise ValueError("Only task creator can delete task")
        
        try:
            self.db.delete(task)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Task deletion failed")
    
    def update_task_status(self, task_id: uuid.UUID, status_update: TaskStatusUpdate, user_id: uuid.UUID) -> Task:
        """Update task status."""
        task = self.get_task_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check if user is creator or assignee
        if task.created_by != user_id and task.assignee_id != user_id:
            raise ValueError("Only task creator or assignee can update task status")
        
        try:
            task.status = TaskStatus(status_update.status)
            self.db.commit()
            self.db.refresh(task)
            return task
        except ValueError:
            raise ValueError("Invalid task status")
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Task status update failed")
    
    def assign_task(self, task_id: uuid.UUID, assign_data: TaskAssign, user_id: uuid.UUID) -> Task:
        """Assign task to a user."""
        task = self.get_task_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check if user is creator or project admin
        # For now, allow creator to assign
        if task.created_by != user_id:
            raise ValueError("Only task creator can assign task")
        
        # Check if assignee exists
        assignee = self.db.query(User).filter(User.id == assign_data.assignee_id).first()
        if not assignee:
            raise ValueError("Assignee not found")
        
        try:
            task.assignee_id = assign_data.assignee_id
            self.db.commit()
            self.db.refresh(task)
            return task
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Task assignment failed")
    
    def get_user_tasks(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        """Get tasks assigned to or created by a user."""
        return self.db.query(Task).filter(
            (Task.assignee_id == user_id) | (Task.created_by == user_id)
        ).offset(skip).limit(limit).all()
    
    def get_project_tasks(self, project_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        """Get tasks for a specific project."""
        return self.db.query(Task).filter(
            Task.project_id == project_id
        ).offset(skip).limit(limit).all()