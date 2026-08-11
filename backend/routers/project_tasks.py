"""
Project Task Management router - handles task operations within project context.
Refactored to use async operations and Dependency Injection.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from async_dependencies import require_project_member
from database import get_async_db
from dependencies.services import (
    get_project_service,
    get_task_service,
)
from models.project import Project
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
from services.job_queue import enqueue_job
from utils.logger import mask_user_id, setup_logger
from utils.response_helpers import build_task_response, normalize_task_status
from utils.validators import validate_uuid

logger = setup_logger("project_tasks_router")

router = APIRouter(prefix="/projects", tags=["project tasks"])
INVALID_PROJECT_ID_DETAIL = "Invalid project ID format"
INVALID_TASK_ID_DETAIL = "Invalid task ID format"
TASK_NOT_FOUND_DETAIL = "Task not found"
TASK_NOT_IN_PROJECT_DETAIL = "Task not found in this project"
NOTIFICATION_JOB_TYPE = "notification.dispatch"

# Route-level rate limiting for project task operations
from rate_limiter import RateLimits, limiter


def _get_status_value(status: Any) -> str:
    """Helper function to extract status value from enum or string."""
    return normalize_task_status(status)


def _build_task_response(task: Any) -> dict:
    """Helper to build task response dict using central helper."""
    return build_task_response(task, include_relations=False)


def _build_task_with_details_response(task: Any) -> dict:
    """Helper to build task with details response dict using central helper."""
    return build_task_response(task, include_relations=True)


@router.get("/{project_id}/tasks", response_model=TaskListResponse)
@limiter.limit(RateLimits.API_READ)
async def get_project_tasks(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    sort_by: str | None = Query(None, max_length=30, description="Field to sort by"),
    sort_order: str | None = Query(None, pattern=r"^(asc|desc)$", description="Sort order"),
    search: str | None = Query(
        None, max_length=100, description="Search term for title/description"
    ),
    status_filter: str | None = Query(
        None, alias="status", max_length=30, description="Filter by status"
    ),
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
        logger.exception(f"Exception in get_project_tasks: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project tasks: {e!s}",
        )


@router.post("/{project_id}/tasks", response_model=TaskResponse)
@limiter.limit(RateLimits.TASK_CREATE)
async def create_task_for_project(
    request: Request,
    task_data: TaskCreate,
    project: Project = Depends(require_project_member),
    db: AsyncSession = Depends(get_async_db),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Create a new task for a specific project."""
    logger.info(f"Creating task for project {project.id} by user {mask_user_id(current_user.id)}")

    # Override project_id in task_data to ensure consistency
    task_data.project_id = project.id

    try:
        task = await task_service.create_task(task_data, current_user.id, commit=False)

        if task.assignee_id and task.assignee_id != current_user.id:
            await enqueue_job(
                db,
                NOTIFICATION_JOB_TYPE,
                {
                    "event": "task_assigned",
                    "task_id": str(task.id),
                    "assignee_id": str(task.assignee_id),
                    "assigner_id": str(current_user.id),
                },
                idempotency_key=f"task-assigned:{task.id}:{task.assignee_id}",
            )
        await db.commit()

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
    project_uuid = validate_uuid(project_id, INVALID_PROJECT_ID_DETAIL)
    task_uuid = validate_uuid(task_id, INVALID_TASK_ID_DETAIL)

    if not await project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project"
        )

    try:
        task = await task_service.get_task_by_id(task_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=INVALID_TASK_ID_DETAIL
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND_DETAIL)

    if task.project_id != project_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_IN_PROJECT_DETAIL
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
    task_uuid = validate_uuid(task_id, INVALID_TASK_ID_DETAIL)

    try:
        task = await task_service.get_task_by_id(task_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=INVALID_TASK_ID_DETAIL
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND_DETAIL)

    if task.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_IN_PROJECT_DETAIL
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
    task_uuid = validate_uuid(task_id, INVALID_TASK_ID_DETAIL)

    try:
        task = await task_service.get_task_by_id(task_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=INVALID_TASK_ID_DETAIL
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND_DETAIL)

    if task.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_IN_PROJECT_DETAIL
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
    project: Project = Depends(require_project_member),
    db: AsyncSession = Depends(get_async_db),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update task status by project ID and task ID."""
    task_uuid = validate_uuid(task_id, INVALID_TASK_ID_DETAIL)

    new_status = status_data.get("status")
    if not new_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status is required")

    status_update = TaskStatusUpdate(status=new_status)

    try:
        task = await task_service.get_task_by_id(task_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=INVALID_TASK_ID_DETAIL
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND_DETAIL)

    if task.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_IN_PROJECT_DETAIL
        )

    old_status = _get_status_value(task.status)

    try:
        updated_task = await task_service.update_task_status(
            task_uuid, status_update, current_user.id, commit=False
        )

        if old_status != new_status:
            await enqueue_job(
                db,
                NOTIFICATION_JOB_TYPE,
                {
                    "event": "task_status_changed",
                    "task_id": str(updated_task.id),
                    "changer_id": str(current_user.id),
                    "old_status": old_status,
                    "new_status": new_status,
                    "completed": new_status.lower() in ["done", "completed"],
                },
                idempotency_key=f"task-status:{updated_task.id}:{new_status}:{updated_task.updated_at}",
            )
        await db.commit()

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
    db: AsyncSession = Depends(get_async_db),
    task_service: AsyncTaskService = Depends(get_task_service),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Assign task to a user by project ID and task ID."""
    project_uuid = validate_uuid(project_id, INVALID_PROJECT_ID_DETAIL)
    task_uuid = validate_uuid(task_id, INVALID_TASK_ID_DETAIL)

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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=INVALID_TASK_ID_DETAIL
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND_DETAIL)

    if task.project_id != project_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_IN_PROJECT_DETAIL
        )

    try:
        updated_task = await task_service.assign_task(
            task_uuid, task_assign, current_user.id, commit=False
        )

        assignee_result = await db.execute(select(User).filter(User.id == assignee_uuid))
        assignee = assignee_result.scalars().first()

        if assignee:
            await enqueue_job(
                db,
                NOTIFICATION_JOB_TYPE,
                {
                    "event": "task_assigned",
                    "task_id": str(updated_task.id),
                    "assignee_id": str(assignee_uuid),
                    "assigner_id": str(current_user.id),
                },
                idempotency_key=f"task-assigned:{updated_task.id}:{assignee_uuid}:{updated_task.updated_at}",
            )
        await db.commit()

        return updated_task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
