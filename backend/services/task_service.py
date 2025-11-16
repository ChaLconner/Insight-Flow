"""
Task service layer for task management.
"""
from typing import Optional, List, Dict, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc
from models.task import Task, TaskStatus
from models.project import Project
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
        logger.info(f"Task data type: {type(task_data)}")
        logger.info(f"Task data fields: {task_data.__dict__ if hasattr(task_data, '__dict__') else 'No __dict__'}")
        
        # Check if project exists and user is a member
        project = self.db.query(Project).filter(Project.id == task_data.project_id).first()
        if not project:
            logger.error(f"Project not found: {task_data.project_id}")
            raise ValueError("Project not found")
        
        logger.info(f"Found project: {project.name}")
        
        # Check if assignee exists (if provided)
        if task_data.assignee_id:
            logger.info(f"Checking assignee: {task_data.assignee_id}")
            assignee = self.db.query(User).filter(User.id == task_data.assignee_id).first()
            if not assignee:
                logger.error(f"Assignee not found: {task_data.assignee_id}")
                raise ValueError("Assignee not found")
            logger.info(f"Found assignee: {assignee.name}")
        
        try:
            # Handle status from frontend - convert string to enum if provided
            task_status = TaskStatus.TODO  # Default status
            if task_data.status:
                logger.info(f"Status from frontend: {task_data.status} (type: {type(task_data.status)})")
                try:
                    # Convert string status to enum - handle both lowercase and uppercase
                    status_lower = task_data.status.lower()
                    if status_lower == 'todo':
                        task_status = TaskStatus.TODO
                    elif status_lower == 'in_progress':
                        task_status = TaskStatus.IN_PROGRESS
                    elif status_lower == 'done':
                        task_status = TaskStatus.DONE
                    else:
                        logger.warning(f"Invalid status from frontend: {task_data.status}, using default TODO")
                        task_status = TaskStatus.TODO
                    
                    logger.info(f"Converted status from frontend: {task_data.status} -> {task_status}")
                    logger.info(f"DEBUG: Final enum value to save: {task_status.value}")
                except ValueError as e:
                    logger.warning(f"Invalid status from frontend: {task_data.status}, using default TODO")
                    task_status = TaskStatus.TODO
            
            # DEBUG: Log exact enum value being set
            logger.info(f"DEBUG: Setting task status to enum: {task_status}")
            logger.info(f"DEBUG: Enum value type: {type(task_status)}")
            logger.info(f"DEBUG: Enum string value: {task_status.value if hasattr(task_status, 'value') else str(task_status)}")
            logger.info(f"Setting task status to: {task_status}")
            
            # Create task without explicitly setting ID - let SQLAlchemy handle UUID generation
            db_task = Task(
                title=task_data.title,
                description=task_data.description,
                status=task_status,  # Use converted enum value
                project_id=task_data.project_id,
                assignee_id=task_data.assignee_id,
                created_by=created_by,
                due_date=task_data.due_date
            )
           
            # DEBUG: Log task object before adding to session
            logger.info(f"Created Task object: {db_task}")
            logger.info(f"Task object fields: title={db_task.title}, description={db_task.description}, status={db_task.status}")
            logger.info(f"Task object IDs: project_id={db_task.project_id}, assignee_id={db_task.assignee_id}, created_by={db_task.created_by}")
            logger.info(f"Task object ID before commit: {db_task.id} (type: {type(db_task.id)})")
            
            self.db.add(db_task)
            logger.info("Task added to database session")
            
            # Flush to get ID without committing
            self.db.flush()
            logger.info(f"Task ID after flush: {db_task.id} (type: {type(db_task.id)})")
            
            self.db.commit()
            logger.info("Task committed to database")
            
            self.db.refresh(db_task)
            logger.info(f"Task refreshed with ID: {db_task.id} (type: {type(db_task.id)})")
            
        except IntegrityError as e:
            logger.error(f"IntegrityError during task creation: {e}")
            logger.error(f"IntegrityError details: {e.args}")
            logger.error(f"IntegrityError orig: {e.orig}")
            logger.error(f"IntegrityError statement: {e.statement}")
            logger.error(f"IntegrityError params: {e.params}")
            self.db.rollback()
            
            # Extract more specific error message
            error_message = "Task creation failed"
            if e.orig:
                if hasattr(e.orig, 'pgerror') and e.orig.pgerror:
                    error_message = f"Database error: {e.orig.pgerror}"
                elif hasattr(e.orig, 'args') and e.orig.args:
                    error_message = f"Database error: {str(e.orig.args[0])}"
                else:
                    error_message = f"Database error: {str(e.orig)}"
            
            logger.error(f"Raising ValueError with message: {error_message}")
            raise ValueError(error_message)
        except Exception as e:
            logger.error(f"Unexpected error during task creation: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            logger.error(f"Error args: {e.args}")
            if hasattr(e, '__traceback__'):
                import traceback
                logger.error(f"Error traceback: {traceback.format_exc()}")
            self.db.rollback()
            raise ValueError(f"Task creation failed: {str(e)}")
        
        # Validate that we have a proper UUID
        if not db_task.id:
            logger.error("ERROR: Task ID is None after commit!")
            raise ValueError("Task ID was not generated properly")
        
        if not isinstance(db_task.id, uuid.UUID):
            logger.error(f"ERROR: Task ID is not a UUID! Got: {db_task.id} (type: {type(db_task.id)})")
            raise ValueError(f"Task ID is not a UUID: {db_task.id}")
       
        # Log task creation activity
        logger.info("Logging task creation activity")
        self.task_history_service.log_task_created(db_task, created_by)
        logger.info("Task creation activity logged")
       
        # Log task assignment if assignee is provided
        if task_data.assignee_id:
            logger.info("Logging task assignment activity")
            self.task_history_service.log_task_assigned(db_task, task_data.assignee_id, created_by)
            logger.info("Task assignment activity logged")
       
        return db_task
    
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
        
        # Store old values for activity logging
        old_values: Dict[str, Union[str, uuid.UUID, TaskStatus]] = {}
        new_values: Dict[str, Union[str, uuid.UUID, TaskStatus]] = {}
        
        # Initialize old_assignee_id
        old_assignee_id = task.assignee_id
        
        # Update fields if provided and track changes
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
                # Convert string to enum with proper mapping - handle both lowercase and uppercase
                status_lower = task_data.status.lower()
                if status_lower == 'todo':
                    new_status = TaskStatus.TODO
                elif status_lower == 'in_progress':
                    new_status = TaskStatus.IN_PROGRESS
                elif status_lower == 'done':
                    new_status = TaskStatus.DONE
                else:
                    raise ValueError("Invalid task status")
                    
                if new_status != task.status:
                    old_values["status"] = task.status
                    new_values["status"] = task_data.status
                    task.status = new_status
            except ValueError:
                raise ValueError("Invalid task status")
                
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
           
            # Log update activity if there were changes
            if old_values or new_values:
                self.task_history_service.log_task_updated(task, user_id, old_values, new_values)
           
            # Log task assignment if assignee changed
            if task_data.assignee_id and task_data.assignee_id != old_assignee_id:
                self.task_history_service.log_task_assigned(task, task_data.assignee_id, user_id)
           
            # Log task completion if status changed to done
            if task_data.status and task_data.status.lower() == 'done' and task.status == 'done':
                self.task_history_service.log_task_completed(task, user_id)
           
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
        
        # Log task deletion activity before deleting
        self.task_history_service.log_task_deleted(task, user_id)
            
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
        
        # Store old status for activity logging
        old_status = task.status
        
        try:
            # Convert string to enum with proper mapping - handle both lowercase and uppercase
            status_lower = status_update.status.lower()
            if status_lower == 'todo':
                task.status = TaskStatus.TODO
            elif status_lower == 'in_progress':
                task.status = TaskStatus.IN_PROGRESS
            elif status_lower == 'done':
                task.status = TaskStatus.DONE
            else:
                raise ValueError("Invalid task status")
                
            self.db.commit()
            self.db.refresh(task)
            
            # Log task status change activity
            if old_status != task.status:
                if task.status.value.lower() == 'done':
                    self.task_history_service.log_task_completed(task, user_id)
                else:
                    self.task_history_service.log_task_updated(task, user_id, 
                        {"status": old_status},
                        {"status": task.status.value})
            
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
            
            # Log task assignment activity
            self.task_history_service.log_task_assigned(task, assign_data.assignee_id, user_id)
            
            return task
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Task assignment failed")
    
    def get_user_tasks(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        """Get tasks assigned to or created by a user."""
        return self.db.query(Task).filter(
            (Task.assignee_id == user_id) | (Task.created_by == user_id)
        ).offset(skip).limit(limit).all()
    
    def get_project_tasks(self, project_id: uuid.UUID, skip: int = 0, limit: int = 100, 
                        sort_by: Optional[str] = None, sort_order: Optional[str] = None) -> List[Task]:
        """Get tasks for a specific project with optional sorting."""
        from sqlalchemy.orm import joinedload
        
        logger.info(f"DEBUG: get_project_tasks called with:")
        logger.info(f"DEBUG: project_id: {project_id}")
        logger.info(f"DEBUG: skip: {skip}")
        logger.info(f"DEBUG: limit: {limit}")
        logger.info(f"DEBUG: sort_by: {sort_by}")
        logger.info(f"DEBUG: sort_order: {sort_order}")
        
        query = self.db.query(Task).options(
            joinedload(Task.assignee),
            joinedload(Task.creator),
            joinedload(Task.project)
        ).filter(Task.project_id == project_id)
        
        # Add sorting if provided
        if sort_by:
            logger.info(f"DEBUG: Adding sorting for field: {sort_by}")
            # Map frontend field names to model attributes
            sort_field_map = {
                'created_at': Task.created_at,
                'updated_at': Task.updated_at,
                'title': Task.title,
                'due_date': Task.due_date,
                'status': Task.status
            }
            
            if sort_by in sort_field_map:
                sort_field = sort_field_map[sort_by]
                logger.info(f"DEBUG: Mapped sort field: {sort_field}")
                
                # Apply sort order
                if sort_order and sort_order.lower() == 'desc':
                    logger.info(f"DEBUG: Applying descending order")
                    query = query.order_by(desc(sort_field))
                else:
                    logger.info(f"DEBUG: Applying ascending order")
                    query = query.order_by(asc(sort_field))
            else:
                logger.warning(f"DEBUG: Invalid sort field: {sort_by}")
        
        logger.info(f"DEBUG: Executing query...")
        tasks = query.offset(skip).limit(limit).all()
        logger.info(f"DEBUG: Query executed, found {len(tasks)} tasks")
        
        return tasks