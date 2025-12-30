"""
Project Task Management router - handles task operations within project context.
Refactored to use async operations and Dependency Injection.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from async_dependencies import require_project_member
from dependencies.services import get_project_service, get_task_service
from models.project import Project
from models.task import TaskStatus
from models.user import User
from routers.auth import get_current_active_user
from schemas.task import (
    TaskAssign,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
    TaskWithDetails,
)
from services.async_project_service import AsyncProjectService
from services.async_task_service import AsyncTaskService
from utils.logger import mask_user_id, setup_logger
from utils.validators import validate_uuid

logger = setup_logger("project_tasks_router")

router = APIRouter(prefix="/projects", tags=["project tasks"])


def _get_status_value(status) -> str:
    """Helper function to extract status value from enum or string."""
    if hasattr(status, "value") or isinstance(status, TaskStatus):
        status_value = status.value
    else:
        status_value = str(status)

    return status_value.lower() if status_value else "todo"


def _build_task_response(task: Any) -> dict:
    """Helper to build task response dict."""
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": _get_status_value(task.status),
        "project_id": task.project_id,
        "assignee_id": task.assignee_id,
        "created_by": task.created_by,
        "due_date": task.due_date,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "priority": task.priority.value if hasattr(task.priority, "value") else task.priority,
        "type": task.type.value if hasattr(task.type, "value") else task.type,
    }


def _build_task_with_details_response(task: Any) -> dict:
    """Helper to build task with details response dict."""
    response = _build_task_response(task)
    response.update(
        {
            "assignee": task.assignee,
            "creator": task.creator,
            "project": task.project,
        }
    )
    return response


@router.get("/{project_id}/tasks", response_model=TaskListResponse)
async def get_project_tasks(
    skip: int = 0,
    limit: int = 100,
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str | None = Query(None, description="Sort order (asc/desc)"),
    search: str | None = Query(None, description="Search term for title/description"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    project: Project = Depends(require_project_member),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get tasks for a specific project."""
    logger.info(f"get_project_tasks: project_id={project.id}, skip={skip}, limit={limit}")

    try:
        tasks, total = await task_service.get_project_tasks(
            project.id,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            status=status_filter,
        )

        items = [
            TaskWithDetails.model_validate(_build_task_with_details_response(task))
            for task in tasks
        ]
        page = (skip // limit) + 1 if limit > 0 else 1
        has_more = total > (skip + limit)

        return TaskListResponse(items=items, total=total, page=page, size=limit, has_more=has_more)
    except Exception as e:
        logger.error(f"Exception in get_project_tasks: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project tasks: {e!s}",
        )


@router.post("/{project_id}/tasks", response_model=TaskResponse)
async def create_task_for_project(
    task_data: TaskCreate,
    project: Project = Depends(require_project_member),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Create a new task for a specific project."""
    logger.info(f"Creating task for project {project.id} by user {mask_user_id(current_user.id)}")

    # Override project_id in task_data to ensure consistency
    task_data.project_id = project.id

    try:
        task = await task_service.create_task(task_data, current_user.id)
        logger.info(f"Task created successfully: {task.id}")
        return TaskResponse.model_validate(_build_task_response(task))
    except ValueError as e:
        logger.warning(f"Error creating task: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{project_id}/tasks/{task_id}", response_model=TaskWithDetails)
async def read_project_task(
    project_id: str,
    task_id: str,
    task_service: AsyncTaskService = Depends(get_task_service),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get task by project ID and task ID with full details."""
    project_uuid = validate_uuid(project_id, "Invalid project ID format")
    task_uuid = validate_uuid(task_id, "Invalid task ID format")

    if not await project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project"
        )

    try:
        task = await task_service.get_task_by_id(task_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid task ID format"
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.project_id != project_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found in this project"
        )

    return TaskWithDetails(**_build_task_with_details_response(task))


@router.put("/{project_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_project_task(
    task_id: str,
    task_data: TaskUpdate,
    project: Project = Depends(require_project_member),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update task information by project ID and task ID."""
    task_uuid = validate_uuid(task_id, "Invalid task ID format")

    try:
        task = await task_service.get_task_by_id(task_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid task ID format"
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found in this project"
        )

    try:
        updated_task = await task_service.update_task(task_uuid, task_data, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{project_id}/tasks/{task_id}")
async def delete_project_task(
    task_id: str,
    project: Project = Depends(require_project_member),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Delete a task by project ID and task ID."""
    task_uuid = validate_uuid(task_id, "Invalid task ID format")

    try:
        task = await task_service.get_task_by_id(task_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid task ID format"
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found in this project"
        )

    try:
        await task_service.delete_task(task_uuid, current_user.id)
        return {"message": "Task deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{project_id}/tasks/{task_id}/status", response_model=TaskResponse)
async def update_project_task_status(
    task_id: str,
    status_data: dict[str, str],
    project: Project = Depends(require_project_member),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update task status by project ID and task ID."""
    task_uuid = validate_uuid(task_id, "Invalid task ID format")

    new_status = status_data.get("status")
    if not new_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status is required")

    status_update = TaskStatusUpdate(status=new_status)

    try:
        task = await task_service.get_task_by_id(task_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid task ID format"
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found in this project"
        )

    try:
        updated_task = await task_service.update_task_status(
            task_uuid, status_update, current_user.id
        )
        return updated_task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{project_id}/tasks/{task_id}/assign", response_model=TaskResponse)
async def assign_project_task(
    project_id: str,
    task_id: str,
    assign_data: dict,
    task_service: AsyncTaskService = Depends(get_task_service),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Assign task to a user by project ID and task ID."""
    project_uuid = validate_uuid(project_id, "Invalid project ID format")
    task_uuid = validate_uuid(task_id, "Invalid task ID format")

    assignee_id = assign_data.get("assignee_id")
    if not assignee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee ID is required"
        )

    assignee_uuid = validate_uuid(assignee_id, "Invalid assignee ID format")
    task_assign = TaskAssign(assignee_id=assignee_uuid)

    if not await project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project"
        )

    try:
        task = await task_service.get_task_by_id(task_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid task ID format"
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.project_id != project_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found in this project"
        )

    try:
        updated_task = await task_service.assign_task(task_uuid, task_assign, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
