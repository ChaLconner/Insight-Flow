"""
Project Task Management router - handles task operations within project context.
Refactored to use async operations and Dependency Injection.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from async_dependencies import require_project_member
from database import get_async_db
from dependencies.services import (
    get_notification_service,
    get_project_service,
    get_task_service,
)
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
from services.async_notification_trigger_service import AsyncNotificationTriggerService
from services.async_project_service import AsyncProjectService
from services.async_task_service import AsyncTaskService
from utils.logger import mask_user_id, setup_logger
from utils.response_helpers import build_task_response
from utils.validators import validate_uuid

logger = setup_logger("project_tasks_router")

router = APIRouter(prefix="/projects", tags=["project tasks"])

# Route-level rate limiting for project task operations
from rate_limiter import RateLimits, limiter


def _get_status_value(status: Any) -> str:
    """Helper function to extract status value from enum or string."""
    if hasattr(status, "value") or isinstance(status, TaskStatus):
        status_value = status.value
    else:
        status_value = str(status)
    return status_value.lower() if status_value else "todo"


def _build_task_response(task: Any) -> dict:
    """Helper to build task response dict using central helper."""
    return build_task_response(task, include_relations=False)


def _build_task_with_details_response(task: Any) -> dict:
    """Helper to build task with details response dict using central helper."""
    res = build_task_response(task, include_relations=True)
    if hasattr(task, "assignee") and task.assignee and "assignee" not in res:
        res["assignee"] = task.assignee
    if hasattr(task, "creator") and task.creator and "creator" not in res:
        res["creator"] = task.creator
    if hasattr(task, "project") and task.project and "project" not in res:
        res["project"] = task.project
    return res


@router.get("/{project_id}/tasks", response_model=TaskListResponse)
@limiter.limit(RateLimits.API_READ)
async def get_project_tasks(
    request: Request,
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
@limiter.limit(RateLimits.TASK_CREATE)
async def create_task_for_project(
    request: Request,
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    project: Project = Depends(require_project_member),
    db: AsyncSession = Depends(get_async_db),
    task_service: AsyncTaskService = Depends(get_task_service),
    notification_service: AsyncNotificationTriggerService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Create a new task for a specific project."""
    logger.info(f"Creating task for project {project.id} by user {mask_user_id(current_user.id)}")

    # Override project_id in task_data to ensure consistency
    task_data.project_id = project.id

    try:
        task = await task_service.create_task(task_data, current_user.id)

        if task.assignee_id and task.assignee_id != current_user.id:
            assignee = task.assignee
            if assignee is None:
                assignee_result = await db.execute(select(User).filter(User.id == task.assignee_id))
                assignee = assignee_result.scalars().first()

            if assignee:

                async def notify_task_created():
                    await notification_service.notify_task_assigned(
                        assignee=assignee,
                        task_id=task.id,
                        task_title=task.title,
                        project_id=task.project_id,
                        project_name=project.name,
                        assigner=current_user,
                    )

                background_tasks.add_task(notify_task_created)

        logger.info(f"Task created successfully: {task.id}")
        return TaskResponse.model_validate(_build_task_response(task))
    except ValueError as e:
        logger.warning(f"Error creating task: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{project_id}/tasks/{task_id}", response_model=TaskWithDetails)
@limiter.limit(RateLimits.API_READ)
async def read_project_task(
    request: Request,
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
@limiter.limit(RateLimits.TASK_UPDATE)
async def update_project_task(
    request: Request,
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
@limiter.limit(RateLimits.TASK_DELETE)
async def delete_project_task(
    request: Request,
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
@limiter.limit(RateLimits.TASK_UPDATE)
async def update_project_task_status(
    request: Request,
    task_id: str,
    status_data: dict[str, str],
    background_tasks: BackgroundTasks,
    project: Project = Depends(require_project_member),
    task_service: AsyncTaskService = Depends(get_task_service),
    notification_service: AsyncNotificationTriggerService = Depends(get_notification_service),
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

    old_status = _get_status_value(task.status)

    try:
        updated_task = await task_service.update_task_status(
            task_uuid, status_update, current_user.id
        )

        if old_status != new_status:

            async def send_status_notification():
                await notification_service.notify_task_status_changed(
                    task_id=updated_task.id,
                    task_title=updated_task.title,
                    project_id=task.project_id,
                    old_status=old_status,
                    new_status=new_status,
                    changer=current_user,
                    assignee=task.assignee,
                    creator=task.creator,
                )

                if new_status.lower() in ["done", "completed"]:
                    await notification_service.notify_task_completed(
                        task_id=updated_task.id,
                        task_title=updated_task.title,
                        project_id=task.project_id,
                        project_name=project.name,
                        completer=current_user,
                        creator=task.creator,
                    )

            background_tasks.add_task(send_status_notification)

        return updated_task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{project_id}/tasks/{task_id}/assign", response_model=TaskResponse)
@limiter.limit(RateLimits.TASK_UPDATE)
async def assign_project_task(
    request: Request,
    project_id: str,
    task_id: str,
    assign_data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    task_service: AsyncTaskService = Depends(get_task_service),
    project_service: AsyncProjectService = Depends(get_project_service),
    notification_service: AsyncNotificationTriggerService = Depends(get_notification_service),
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

        assignee_result = await db.execute(select(User).filter(User.id == assignee_uuid))
        assignee = assignee_result.scalars().first()

        if assignee:

            async def send_assign_notification():
                await notification_service.notify_task_assigned(
                    assignee=assignee,
                    task_id=updated_task.id,
                    task_title=updated_task.title,
                    project_id=updated_task.project_id,
                    project_name=task.project.name if task.project else "Unknown",
                    assigner=current_user,
                )

            background_tasks.add_task(send_assign_notification)

        return updated_task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
