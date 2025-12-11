"""
Task management router for CRUD operations.
"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from schemas.task import TaskResponse, TaskCreate, TaskUpdate, TaskWithDetails, TaskStatusUpdate, TaskAssign, TaskListResponse
from models.task import Task, TaskStatus
from models.user import User
from services.task_service import TaskService

from database import get_db
from dependencies import get_authorized_task
from routers.auth import get_current_active_user
from utils.logger import setup_logger
import uuid

def map_task_to_response(task: Task) -> TaskWithDetails:
    """Helper to map Task model to TaskWithDetails schema with normalized status."""
    # Properly handle TaskStatus enum conversion and ensure lowercase
    status_value = str(task.status.value if hasattr(task.status, 'value') else task.status).lower()
    status_value = status_value if status_value else 'todo'
        
    return TaskWithDetails(
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
        project=task.project,
        priority=task.priority.value if hasattr(task.priority, 'value') else task.priority,
        type=task.type.value if hasattr(task.type, 'value') else task.type
    )

# The logger sends the logs to the root logger
logger = setup_logger("tasks_router")
router = APIRouter()

# IMPORTANT: This route must be defined BEFORE /{task_id} to prevent "my" being captured as task_id
@router.get("/my/tasks", response_model=TaskListResponse)
def get_my_tasks(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get tasks assigned to or created by current user.
    """
    task_service = TaskService(db)
    tasks, total = task_service.get_user_tasks(
        current_user.id,
        skip=skip,
        limit=limit,
        search=search,
        status=status
    )
    
    # Calculate pagination metadata
    page = (skip // limit) + 1 if limit > 0 else 1
    has_more = total > (skip + limit)
    
    # Convert tasks to response format with full details
    items = [map_task_to_response(task) for task in tasks]
    
    return TaskListResponse(
        items=items,
        total=total,
        page=page,
        size=limit,
        has_more=has_more
    )

@router.post("/", response_model=TaskResponse)
def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new task.
    """
    task_service = TaskService(db)
    
    try:
        task = task_service.create_task(task_data, current_user.id, background_tasks)
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/", response_model=TaskListResponse)
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
    tasks, total = task_service.get_user_tasks(
        current_user.id, 
        skip=skip, 
        limit=limit,
        search=search,
        status=status
    )
    
    # Calculate pagination metadata
    page = (skip // limit) + 1 if limit > 0 else 1
    has_more = total > (skip + limit)
    
    # Convert tasks to response format with full details
    items = [map_task_to_response(task) for task in tasks]
    
    return TaskListResponse(
        items=items,
        total=total,
        page=page,
        size=limit,
        has_more=has_more
    )

@router.get("/{task_id}", response_model=TaskWithDetails)
def read_task(
    task: Task = Depends(get_authorized_task),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get task by ID with full details.
    """
    # The dependency already checked permissions, but we fetch again 
    # with eager loading for performance (2 queries total vs 1 + 3 lazy loads)
    task_service = TaskService(db)
    detailed_task = task_service.get_task_with_details(task.id)
    
    if not detailed_task:
        # Should not happen given dependency check
        raise HTTPException(status_code=404, detail="Task not found")
        
    return TaskWithDetails.model_validate(detailed_task)

@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_data: TaskUpdate,
    task: Task = Depends(get_authorized_task),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task information.
    """
    task_service = TaskService(db)
    
    try:
        # Note: task is already fetched and checked for basic membership access by dependency
        updated_task = task_service.update_task(task.id, task_data, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{task_id}")
def delete_task(
    task: Task = Depends(get_authorized_task),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete a task.
    """
    task_service = TaskService(db)
    
    try:
        task_service.delete_task(task.id, current_user.id)
        return {"message": "Task deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{task_id}/status", response_model=TaskResponse)
def update_task_status(
    status_data: dict,
    task: Task = Depends(get_authorized_task),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task status.
    """
    task_service = TaskService(db)
    
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
        updated_task = task_service.update_task_status(task.id, status_update, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{task_id}/assign", response_model=TaskResponse)
def assign_task(
    assign_data: dict,
    task: Task = Depends(get_authorized_task),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Assign task to a user.
    """
    task_service = TaskService(db)
    
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
    
    try:
        updated_task = task_service.assign_task(task.id, task_assign, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )








