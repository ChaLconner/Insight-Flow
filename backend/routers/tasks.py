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

router = APIRouter(prefix="/tasks", tags=["task management"])

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
    
    
    # DEBUG: Enhanced logging for task creation debugging
    logger.info(f"DEBUG TASK CREATION START ===")
    logger.info(f"DEBUG - User ID: {current_user.id}")
    logger.info(f"DEBUG - User email: {current_user.email}")
    logger.info(f"DEBUG - Project ID: {task_data.project_id}")
    logger.info(f"DEBUG - Task data: {task_data}")
    
    # DEBUG: Check project existence first
    project = project_service.get_project_by_id(task_data.project_id)
    if not project:
        logger.error(f"DEBUG - Project not found: {task_data.project_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    logger.info(f"DEBUG - Project found: {project.name}")
    
    # DEBUG: Check all project members
    all_members = project_service.get_project_members(task_data.project_id)
    logger.info(f"DEBUG - All project members: {[{'id': m.user_id, 'name': m.name} for m in all_members]}")
    logger.info(f"DEBUG - Current user in members: {current_user.id in [m.user_id for m in all_members]}")
    logger.info(f"create_task called by user {current_user.id}")
    logger.info(f"Task data received: {task_data}")
    
    # Check if user is a member of project
    if not project_service.is_project_member(task_data.project_id, current_user.id):
        logger.warning(f"User {current_user.id} is not a member of project {task_data.project_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        task = task_service.create_task(task_data, current_user.id)
        logger.info(f"Task created successfully: {task.id}")
        
        # DEBUG: Log task response before returning
        logger.info(f"DEBUG: Preparing task response for ID: {task.id}")
        logger.info(f"DEBUG: Task response data: id={task.id}, title={task.title}, status={task.status}")
        
        # Create response explicitly to ensure all fields are included
        # Ensure status is returned as lowercase to match frontend expectations
        status_value = task.status.value if hasattr(task.status, 'value') else str(task.status)
        status_value = status_value.lower() if status_value else 'todo'
        
        task_response = TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            status=status_value,
            project_id=task.project_id,
            assignee_id=task.assignee_id,
            created_by=task.created_by,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at
        )
        
        logger.info(f"DEBUG: TaskResponse created with ID: {task_response.id} (type: {type(task_response.id)})")
        
        return task_response
    except ValueError as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/task/{task_id}", response_model=TaskWithDetails)
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

@router.get("/projects/{project_id}/tasks/{task_id}", response_model=TaskWithDetails)
def read_project_task(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get task by project ID and task ID with full details.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    try:
        project_uuid = uuid.UUID(project_id)
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID or task ID format"
        )
    
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

@router.put("/task/{task_id}", response_model=TaskResponse)
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

@router.put("/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def update_project_task(
    project_id: str,
    task_id: str,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task information by project ID and task ID.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    try:
        project_uuid = uuid.UUID(project_id)
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID or task ID format"
        )
    
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
        updated_task = task_service.update_task(task_uuid, task_data, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/task/{task_id}")
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

@router.delete("/projects/{project_id}/tasks/{task_id}")
def delete_project_task(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete a task by project ID and task ID.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    try:
        project_uuid = uuid.UUID(project_id)
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID or task ID format"
        )
    
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
        task_service.delete_task(task_uuid, current_user.id)
        return {"message": "Task deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/task/{task_id}/status", response_model=TaskResponse)
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

@router.put("/projects/{project_id}/tasks/{task_id}/status", response_model=TaskResponse)
def update_project_task_status(
    project_id: str,
    task_id: str,
    status_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task status by project ID and task ID.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    try:
        project_uuid = uuid.UUID(project_id)
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID or task ID format"
        )
    
    # Extract status from request body
    status = status_data.get("status")
    if not status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status is required"
        )
    
    # Create TaskStatusUpdate object
    status_update = TaskStatusUpdate(status=status)
    
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
        updated_task = task_service.update_task_status(task_uuid, status_update, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/task/{task_id}/assign", response_model=TaskResponse)
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

@router.put("/projects/{project_id}/tasks/{task_id}/assign", response_model=TaskResponse)
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
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    try:
        project_uuid = uuid.UUID(project_id)
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID or task ID format"
        )
    
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

@router.get("/projects/{project_id}/tasks", response_model=List[TaskWithDetails])
def get_project_tasks(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query(None, description="Sort order (asc/desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get tasks for a specific project.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # DEBUG: Add logging to validate sorting parameters
    logger.info(f"DEBUG: get_project_tasks called with params:")
    logger.info(f"DEBUG: project_id: {project_id}")
    logger.info(f"DEBUG: skip: {skip}")
    logger.info(f"DEBUG: limit: {limit}")
    logger.info(f"DEBUG: sort_by: {sort_by}")
    logger.info(f"DEBUG: sort_order: {sort_order}")
    logger.info(f"DEBUG: current_user: {current_user.id}")
    
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        logger.error(f"DEBUG: Invalid project ID format: {project_id}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Check if user is a member of project
    if not project_service.is_project_member(project_uuid, current_user.id):
        logger.warning(f"DEBUG: User {current_user.id} is not a member of project {project_uuid}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        logger.info(f"DEBUG: Calling task_service.get_project_tasks with sorting params")
        tasks = task_service.get_project_tasks(
            project_uuid, 
            skip=skip, 
            limit=limit, 
            sort_by=sort_by, 
            sort_order=sort_order
        )
        logger.info(f"Found {len(tasks)} tasks for project {project_id}")
        logger.debug(f"Tasks data: {[{'id': str(t.id), 'title': t.title} for t in tasks]}")
        
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
    except Exception as e:
        logger.error(f"DEBUG: Exception in get_project_tasks: {str(e)}")
        logger.error(f"DEBUG: Exception type: {type(e)}")
        import traceback
        logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project tasks: {str(e)}"
        )

@router.post("/projects/{project_id}/tasks", response_model=TaskResponse)
def create_task_for_project(
    project_id: str,
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new task for a specific project.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    logger.info(f"create_task_for_project called with project_id={project_id}")
    logger.info(f"Task data: {task_data}")
    logger.info(f"Current user: {current_user.id}")
    
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        logger.error(f"Invalid project ID format: {project_id}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Override project_id in task_data to ensure consistency
    task_data.project_id = project_uuid
    
    # Check if user is a member of project
    if not project_service.is_project_member(project_uuid, current_user.id):
        logger.warning(f"User {current_user.id} is not a member of project {project_uuid}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        task = task_service.create_task(task_data, current_user.id)
        logger.info(f"Task created successfully: {task.id}")
        
        # DEBUG: Log task response before returning
        logger.info(f"DEBUG: Preparing task response for ID: {task.id}")
        logger.info(f"DEBUG: Task response data: id={task.id}, title={task.title}, status={task.status}")
        
        # Create response explicitly to ensure all fields are included
        # Ensure status is returned as lowercase to match frontend expectations
        status_value = task.status.value if hasattr(task.status, 'value') else str(task.status)
        status_value = status_value.lower() if status_value else 'todo'
        
        task_response = TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            status=status_value,
            project_id=task.project_id,
            assignee_id=task.assignee_id,
            created_by=task.created_by,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at
        )
        
        logger.info(f"DEBUG: TaskResponse created with ID: {task_response.id} (type: {type(task_response.id)})")
        
        return task_response
    except ValueError as e:
        logger.warning(f"Error creating task: {e}")
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


@router.get("/", response_model=List[TaskWithDetails])
def get_all_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get all tasks the user has access to (across all projects they're a member of).
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