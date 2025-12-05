"""
Task management router for CRUD operations.
"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from schemas.task import TaskResponse, TaskCreate, TaskUpdate, TaskWithDetails, TaskStatusUpdate, TaskAssign
from models.task import Task, TaskStatus
from models.user import User
from services.task_service import TaskService
from services.project_service import ProjectService
from database import get_db
from routers.auth import get_current_active_user
from utils.logger import setup_logger
import uuid

# The logger sends the logs to the root logger
logger = setup_logger("tasks_router")
router = APIRouter()

@router.get("/", response_model=List[TaskWithDetails])
def get_all_tasks(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get all tasks the user has access to with optional filtering.
    """
    task_service = TaskService(db)
    tasks = task_service.get_user_tasks(
        current_user.id, 
        skip=skip, 
        limit=limit,
        search=search,
        status=status
    )
    
    # Convert tasks to response format with full details
    task_responses = []
    for task in tasks:
        # Fixed: Properly handle TaskStatus enum conversion and ensure lowercase
        status_value = ""
        if hasattr(task.status, 'value'):
            status_value = task.status.value
        elif isinstance(task.status, TaskStatus):
            status_value = task.status.value
        else:
            status_value = str(task.status)
        
        # Ensure status is returned as lowercase to match frontend expectations
        status_value = status_value.lower() if status_value else 'todo'
            
        task_response = TaskWithDetails(
            id=task.id,
            title=task.title,
            description=task.description,
            status=status_value,
            project_id=task.project_id,
            assignee_id=task.assignee_id,
            created_by=task.created_by,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            assignee=task.assignee,
            creator=task.creator,
            project=task.project
        )
        task_responses.append(task_response)
    
    return task_responses

@router.get("/{task_id}", response_model=TaskWithDetails)
def read_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get task by ID with full details.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    try:
        task = task_service.get_task_by_id(uuid.UUID(task_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid task ID format"
        )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if user is a member of project
    if not project_service.is_project_member(task.project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    # Ensure status is returned as lowercase to match frontend expectations
    status_value = task.status.value if hasattr(task.status, 'value') else str(task.status)
    status_value = status_value.lower() if status_value else 'todo'
    
    # Create response with full details
    task_response = TaskWithDetails(
        id=task.id,
        title=task.title,
        description=task.description,
        status=status_value,
        project_id=task.project_id,
        assignee_id=task.assignee_id,
        created_by=task.created_by,
        due_date=task.due_date,
        created_at=task.created_at,
        updated_at=task.updated_at,
        assignee=task.assignee,
        creator=task.creator,
        project=task.project
    )
    
    return task_response



@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task information.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    try:
        task = task_service.get_task_by_id(uuid.UUID(task_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid task ID format"
        )
    if task and not project_service.is_project_member(task.project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        updated_task = task_service.update_task(uuid.UUID(task_id), task_data, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )



@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete a task.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    try:
        task = task_service.get_task_by_id(uuid.UUID(task_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid task ID format"
        )
    if task and not project_service.is_project_member(task.project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        task_service.delete_task(uuid.UUID(task_id), current_user.id)
        return {"message": "Task deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )



@router.put("/{task_id}/status", response_model=TaskResponse)
def update_task_status(
    task_id: str,
    status_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task status.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Extract status from request body
    status = status_data.get("status")
    if not status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status is required"
        )
    
    # Create TaskStatusUpdate object
    status_update = TaskStatusUpdate(status=status)
    
    try:
        task = task_service.get_task_by_id(uuid.UUID(task_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid task ID format"
        )
    if task and not project_service.is_project_member(task.project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        updated_task = task_service.update_task_status(uuid.UUID(task_id), status_update, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )



@router.put("/{task_id}/assign", response_model=TaskResponse)
def assign_task(
    task_id: str,
    assign_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Assign task to a user.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Extract assignee_id from request body
    assignee_id = assign_data.get("assignee_id")
    if not assignee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee ID is required"
        )
    
    # Create TaskAssign object
    try:
        assignee_uuid = uuid.UUID(assignee_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid assignee ID format"
        )
    
    task_assign = TaskAssign(assignee_id=assignee_uuid)
    
    task = task_service.get_task_by_id(uuid.UUID(task_id))
    if task and not project_service.is_project_member(task.project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        updated_task = task_service.assign_task(uuid.UUID(task_id), task_assign, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )








@router.get("/my/tasks", response_model=List[TaskResponse])
def get_my_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get tasks assigned to or created by current user.
    """
    task_service = TaskService(db)
    tasks = task_service.get_user_tasks(current_user.id, skip=skip, limit=limit)
    
    # Convert tasks to response format with full details
    task_responses = []
    for task in tasks:
        # Fixed: Properly handle TaskStatus enum conversion and ensure lowercase
        status_value = ""
        if hasattr(task.status, 'value'):
            status_value = task.status.value
        elif isinstance(task.status, TaskStatus):
            status_value = task.status.value
        else:
            status_value = str(task.status)
        
        # Ensure status is returned as lowercase to match frontend expectations
        status_value = status_value.lower() if status_value else 'todo'
            
        task_responses.append(TaskWithDetails(
            id=task.id,
            title=task.title,
            description=task.description,
            status=status_value,
            project_id=task.project_id,
            assignee_id=task.assignee_id,
            created_by=task.created_by,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            assignee=task.assignee,
            creator=task.creator,
            project=task.project
        ))
    return task_responses
