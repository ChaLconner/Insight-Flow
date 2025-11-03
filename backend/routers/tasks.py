"""
Task management router for CRUD operations.
"""
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from schemas.task import TaskResponse, TaskCreate, TaskUpdate, TaskWithDetails, TaskStatusUpdate, TaskAssign
from models.task import Task
from models.user import User
from services.task_service import TaskService
from services.project_service import ProjectService
from database import get_db
from routers.auth import get_current_active_user

router = APIRouter(prefix="/tasks", tags=["task management"])

@router.get("/", response_model=List[TaskResponse])
def read_tasks(
    skip: int = 0,
    limit: int = 100,
    project_id: str = Query(None, description="Filter by project ID"),
    assignee_id: str = Query(None, description="Filter by assignee ID"),
    status: str = Query(None, description="Filter by status"),
    my_tasks: bool = Query(False, description="Filter to show only user's tasks"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Retrieve tasks with pagination and optional filters.
    """
    import uuid
    task_service = TaskService(db)
    
    # Convert string parameters to UUID if provided
    project_uuid = uuid.UUID(project_id) if project_id else None
    assignee_uuid = uuid.UUID(assignee_id) if assignee_id else None
    status_enum = None
    
    if status:
        try:
            from models.task import TaskStatus
            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid task status"
            )
    
    # Get user's tasks if requested
    if my_tasks:
        tasks = task_service.get_user_tasks(current_user.id, skip=skip, limit=limit)
    else:
        tasks = task_service.get_tasks(
            skip=skip, 
            limit=limit, 
            project_id=project_uuid, 
            assignee_id=assignee_uuid, 
            status=status_enum
        )
    
    return tasks

@router.post("/", response_model=TaskResponse)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new task.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Check if user is a member of the project
    if not project_service.is_project_member(task_data.project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        task = task_service.create_task(task_data, current_user.id)
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

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
    
    # Check if user is a member of the project
    if not project_service.is_project_member(task.project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    # Create response with full details
    task_response = TaskWithDetails(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value,
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
    
    # Check if user is a member of the project
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
    
    # Check if user is a member of the project
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
    status_update: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task status.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Check if user is a member of the project
    try:
        try:
            task = task_service.get_task_by_id(uuid.UUID(task_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid task ID format"
            )
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
    assign_data: TaskAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Assign task to a user.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Check if user is a member of the project
    task = task_service.get_task_by_id(uuid.UUID(task_id))
    if task and not project_service.is_project_member(task.project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        updated_task = task_service.assign_task(uuid.UUID(task_id), assign_data, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/project/{project_id}", response_model=List[TaskResponse])
def get_project_tasks(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get all tasks for a specific project.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Check if user is a member of the project
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    if not project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    tasks = task_service.get_project_tasks(project_uuid, skip=skip, limit=limit)
    return tasks

@router.get("/my/tasks", response_model=List[TaskResponse])
def get_my_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get tasks assigned to or created by the current user.
    """
    task_service = TaskService(db)
    tasks = task_service.get_user_tasks(current_user.id, skip=skip, limit=limit)
    return tasks