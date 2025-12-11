"""
Project Task Management router - handles task operations within project context.
Refactored from projects.py to improve maintainability.
"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from schemas.task import (
    TaskResponse, TaskCreate, TaskUpdate, TaskWithDetails, 
    TaskStatusUpdate, TaskAssign, TaskListResponse
)
from models.task import TaskStatus
from models.user import User
from models.project import Project
from services.project_service import ProjectService
from services.task_service import TaskService
from database import get_db
from routers.auth import get_current_active_user
from utils.logger import setup_logger
from utils.validators import validate_uuid
from dependencies import require_project_member

logger = setup_logger("project_tasks_router")

router = APIRouter(prefix="/projects", tags=["project tasks"])


@router.get("/{project_id}/tasks", response_model=TaskListResponse)
def get_project_tasks(
    skip: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query(None, description="Sort order (asc/desc)"),
    search: Optional[str] = Query(None, description="Search term for title/description"),
    status: Optional[str] = Query(None, description="Filter by status"),
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get tasks for a specific project.
    """
    task_service = TaskService(db)
    
    logger.info(f"get_project_tasks called with params:")
    logger.info(f"project_id: {project.id}, skip: {skip}, limit: {limit}")
    logger.info(f"sort_by: {sort_by}, sort_order: {sort_order}")
    logger.info(f"search: {search}, status: {status}")
    
    try:
        tasks, total = task_service.get_project_tasks(
            project.id, 
            skip=skip, 
            limit=limit, 
            sort_by=sort_by, 
            sort_order=sort_order,
            search=search,
            status=status
        )
        logger.info(f"Found {len(tasks)} tasks for project {project.id} (Total: {total})")
        
        # Convert tasks to response format with full details
        items = []
        for task in tasks:
            # Properly handle TaskStatus enum conversion
            status_value = _get_status_value(task.status)
            
            task_response = TaskWithDetails.model_validate({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': status_value,
                'project_id': task.project_id,
                'assignee_id': task.assignee_id,
                'created_by': task.created_by,
                'due_date': task.due_date,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'assignee': task.assignee,
                'creator': task.creator,
                'project': task.project,
                'priority': task.priority.value if hasattr(task.priority, 'value') else task.priority,
                'type': task.type.value if hasattr(task.type, 'value') else task.type
            })
            items.append(task_response)
        
        # Calculate pagination metadata
        page = (skip // limit) + 1 if limit > 0 else 1
        has_more = total > (skip + limit)
        
        return TaskListResponse(
            items=items,
            total=total,
            page=page,
            size=limit,
            has_more=has_more
        )
    except Exception as e:
        logger.error(f"Exception in get_project_tasks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project tasks: {str(e)}"
        )


@router.post("/{project_id}/tasks", response_model=TaskResponse)
def create_task_for_project(
    task_data: TaskCreate,
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new task for a specific project.
    """
    task_service = TaskService(db)
    
    logger.info(f"Creating task for project {project.id}")
    logger.info(f"Task data: {task_data}")
    
    # Override project_id in task_data to ensure consistency
    task_data.project_id = project.id
    
    try:
        task = task_service.create_task(task_data, current_user.id)
        logger.info(f"Task created successfully: {task.id}")
        
        # Ensure status is returned as lowercase
        status_value = _get_status_value(task.status)
        
        task_response = TaskResponse.model_validate({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': status_value,
            'project_id': task.project_id,
            'assignee_id': task.assignee_id,
            'created_by': task.created_by,
            'due_date': task.due_date,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
            'priority': task.priority.value if hasattr(task.priority, 'value') else task.priority,
            'type': task.type.value if hasattr(task.type, 'value') else task.type
        })
        
        return task_response
    except ValueError as e:
        logger.warning(f"Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{project_id}/tasks/{task_id}", response_model=TaskWithDetails)
def read_project_task(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get task by project ID and task ID with full details.
    """
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Validate UUIDs
    project_uuid = validate_uuid(project_id, "Invalid project ID format")
    task_uuid = validate_uuid(task_id, "Invalid task ID format")
    
    # Check if user is a member of project first
    if not project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        task = task_service.get_task_by_id(task_uuid)
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
    
    # Verify task belongs to specified project
    if task.project_id != project_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this project"
        )
    
    # Ensure status is returned as lowercase
    status_value = _get_status_value(task.status)
    
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
        project=task.project,
        priority=task.priority.value if hasattr(task.priority, 'value') else task.priority,
        type=task.type.value if hasattr(task.type, 'value') else task.type
    )
    
    return task_response


@router.put("/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def update_project_task(
    task_id: str,
    task_data: TaskUpdate,
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task information by project ID and task ID.
    """
    task_service = TaskService(db)
    
    # Validate UUIDs
    task_uuid = validate_uuid(task_id, "Invalid task ID format")
    
    try:
        task = task_service.get_task_by_id(task_uuid)
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
    
    # Verify task belongs to specified project
    if task.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this project"
        )
    
    try:
        updated_task = task_service.update_task(task_uuid, task_data, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{project_id}/tasks/{task_id}")
def delete_project_task(
    task_id: str,
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete a task by project ID and task ID.
    """
    task_service = TaskService(db)
    
    # Validate UUIDs
    task_uuid = validate_uuid(task_id, "Invalid task ID format")
    
    try:
        task = task_service.get_task_by_id(task_uuid)
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
    
    # Verify task belongs to specified project
    if task.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this project"
        )
    
    try:
        task_service.delete_task(task_uuid, current_user.id)
        return {"message": "Task deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{project_id}/tasks/{task_id}/status", response_model=TaskResponse)
def update_project_task_status(
    task_id: str,
    status_data: dict[str, str],
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task status by project ID and task ID.
    """
    task_service = TaskService(db)
    
    # Validate UUIDs
    task_uuid = validate_uuid(task_id, "Invalid task ID format")
    
    # Extract status from request body
    new_status = status_data.get("status")
    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status is required"
        )
    
    # Create TaskStatusUpdate object
    status_update = TaskStatusUpdate(status=new_status)
    
    try:
        task = task_service.get_task_by_id(task_uuid)
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
    
    # Verify task belongs to specified project
    if task.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this project"
        )
    
    try:
        updated_task = task_service.update_task_status(task_uuid, status_update, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{project_id}/tasks/{task_id}/assign", response_model=TaskResponse)
def assign_project_task(
    project_id: str,
    task_id: str,
    assign_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Assign task to a user by project ID and task ID.
    """
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Validate UUIDs
    project_uuid = validate_uuid(project_id, "Invalid project ID format")
    task_uuid = validate_uuid(task_id, "Invalid task ID format")
    
    # Extract assignee_id from request body
    assignee_id = assign_data.get("assignee_id")
    if not assignee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee ID is required"
        )
    
    # Create TaskAssign object
    assignee_uuid = validate_uuid(assignee_id, "Invalid assignee ID format")
    task_assign = TaskAssign(assignee_id=assignee_uuid)
    
    # Check if user is a member of project first
    if not project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        task = task_service.get_task_by_id(task_uuid)
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
    
    # Verify task belongs to specified project
    if task.project_id != project_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this project"
        )
    
    try:
        updated_task = task_service.assign_task(task_uuid, task_assign, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


def _get_status_value(status) -> str:
    """Helper function to extract status value from enum or string."""
    if hasattr(status, 'value'):
        status_value = status.value
    elif isinstance(status, TaskStatus):
        status_value = status.value
    else:
        status_value = str(status)
    
    return status_value.lower() if status_value else 'todo'
