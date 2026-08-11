"""
Task management router for CRUD operations.
Refactored for Async operations with proper Dependency Injection.
"""

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from async_dependencies import get_async_authorized_task
from database import get_async_db
from dependencies.services import get_task_service
from models.analytics import TaskComment
from models.project import Project, ProjectMember
from models.task import Task
from models.user import User
from routers.auth import get_current_active_user
from schemas.task import (
    TaskAssign,
    TaskCommentCreate,
    TaskCommentResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
    TaskWithDetails,
)
from services.async_task_service import AsyncTaskService
from services.job_queue import enqueue_job
from utils.logger import mask_user_id, setup_logger
from utils.response_helpers import build_task_response

MENTION_PATTERN = re.compile(r"(?<!\w)@(\w{1,255})")
MAX_MENTION_RECIPIENTS = 20
NOTIFICATION_JOB_TYPE = "notification.dispatch"


def map_task_to_response(task: Task) -> dict[str, Any]:
    """Helper to map Task model to dict for TaskWithDetails schema with normalized status."""
    return build_task_response(task, include_relations=True)


def parse_comment_mentions(content: str) -> list[str]:
    """Extract unique mentioned usernames from comment content."""
    mentions: list[str] = []
    seen: set[str] = set()
    for match in MENTION_PATTERN.findall(content):
        normalized = match.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            mentions.append(normalized)
    return mentions


def build_task_comment_response(comment: TaskComment) -> dict[str, Any]:
    """Serialize a task comment for API responses."""
    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "user_id": comment.user_id,
        "content": comment.content,
        "is_edited": str(comment.is_edited).lower() == "true",
        "mentions": parse_comment_mentions(comment.content),
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
        "user": comment.user,
    }


logger = setup_logger("tasks_router")
router = APIRouter()

# Route-level rate limiting for task operations
from rate_limiter import RateLimits, limiter


@router.get("/my/tasks", response_model=TaskListResponse)
@limiter.limit(RateLimits.API_READ)
async def get_my_tasks(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    status: str | None = None,
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get tasks assigned to or created by current user."""
    tasks, total = await task_service.get_user_tasks(
        current_user.id, skip=skip, limit=limit, search=search, status=status
    )

    page = (skip // limit) + 1 if limit > 0 else 1
    has_more = total > (skip + limit)
    items = [TaskWithDetails.model_validate(map_task_to_response(task)) for task in tasks]

    return TaskListResponse(items=items, total=total, page=page, size=limit, has_more=has_more)


@router.post("/", response_model=TaskResponse)
@limiter.limit(RateLimits.TASK_CREATE)
async def create_task(
    request: Request,
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_async_db),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Create a new task."""
    try:
        task = await task_service.create_task(task_data, current_user.id, commit=False)

        # Persist notification intent before returning; the worker sends it
        # with a fresh session after the response.
        if task.assignee_id and task.assignee_id != current_user.id:
            project = await db.get(Project, task.project_id)
            if project:
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

        logger.info(f"Task created by user {mask_user_id(current_user.id)}: {task.id}")
        return task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=TaskListResponse)
@limiter.limit(RateLimits.API_READ)
async def get_all_tasks(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    status: str | None = None,
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get all tasks the user has access to with optional filtering."""
    tasks, total = await task_service.get_user_tasks(
        current_user.id, skip=skip, limit=limit, search=search, status=status
    )

    page = (skip // limit) + 1 if limit > 0 else 1
    has_more = total > (skip + limit)
    items = [TaskWithDetails.model_validate(map_task_to_response(task)) for task in tasks]

    return TaskListResponse(items=items, total=total, page=page, size=limit, has_more=has_more)


@router.get(
    "/{task_id}",
    response_model=TaskWithDetails,
    responses={404: {"description": "Task not found"}},
)
async def read_task(
    task: Task = Depends(get_async_authorized_task),
    task_service: AsyncTaskService = Depends(get_task_service),
) -> Any:
    """Get task by ID with full details."""
    detailed_task = await task_service.get_task_with_details(task.id)

    if not detailed_task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskWithDetails.model_validate(detailed_task)


@router.get("/{task_id}/comments", response_model=list[TaskCommentResponse])
@limiter.limit(RateLimits.API_READ)
async def get_task_comments(
    request: Request,
    task: Task = Depends(get_async_authorized_task),
    db: AsyncSession = Depends(get_async_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> Any:
    """Get a bounded page of comments for a task."""
    result = await db.execute(
        select(TaskComment)
        .options(selectinload(TaskComment.user))
        .filter(TaskComment.task_id == task.id)
        .order_by(TaskComment.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    comments = result.scalars().all()
    return [
        TaskCommentResponse.model_validate(build_task_comment_response(comment))
        for comment in comments
    ]


@router.post("/{task_id}/comments", response_model=TaskCommentResponse)
@limiter.limit(RateLimits.API_WRITE)
async def create_task_comment(
    request: Request,
    comment_data: TaskCommentCreate,
    task: Task = Depends(get_async_authorized_task),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Create a comment on a task and notify mentioned users."""
    comment = TaskComment(task_id=task.id, user_id=current_user.id, content=comment_data.content)
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    comment.user = current_user

    mentioned_usernames = parse_comment_mentions(comment.content)[:MAX_MENTION_RECIPIENTS]
    if mentioned_usernames:
        mentioned_result = await db.execute(
            select(User)
            .join(Project, Project.id == task.project_id)
            .outerjoin(
                ProjectMember,
                and_(
                    ProjectMember.project_id == task.project_id,
                    ProjectMember.user_id == User.id,
                ),
            )
            .filter(
                func.lower(User.username).in_(mentioned_usernames),
                User.is_active.is_(True),
                or_(User.id == Project.owner_id, ProjectMember.user_id.is_not(None)),
            )
            .distinct()
        )
        mentioned_users = mentioned_result.scalars().all()
        for mentioned_user in mentioned_users:
            if mentioned_user.id == current_user.id:
                continue
            await enqueue_job(
                db,
                NOTIFICATION_JOB_TYPE,
                {
                    "event": "mention",
                    "mentioned_user_id": str(mentioned_user.id),
                    "actor_id": str(current_user.id),
                    "message": comment.content,
                    "project_id": str(task.project_id),
                    "task_id": str(task.id),
                },
                idempotency_key=f"mention:{comment.id}:{mentioned_user.id}",
            )
    await db.commit()

    return TaskCommentResponse.model_validate(build_task_comment_response(comment))


@router.put("/{task_id}", response_model=TaskResponse)
@limiter.limit(RateLimits.TASK_UPDATE)
async def update_task(
    request: Request,
    task_data: TaskUpdate,
    task: Task = Depends(get_async_authorized_task),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update task information."""
    try:
        updated_task = await task_service.update_task(task.id, task_data, current_user.id)
        return updated_task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{task_id}")
@limiter.limit(RateLimits.TASK_DELETE)
async def delete_task(
    request: Request,
    task: Task = Depends(get_async_authorized_task),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Delete a task."""
    try:
        await task_service.delete_task(task.id, current_user.id)
        logger.info(f"Task deleted by user {mask_user_id(current_user.id)}: {task.id}")
        return {"message": "Task deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{task_id}/status", response_model=TaskResponse)
@limiter.limit(RateLimits.TASK_UPDATE)
async def update_task_status(
    request: Request,
    status_data: dict,
    db: AsyncSession = Depends(get_async_db),
    task: Task = Depends(get_async_authorized_task),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update task status."""
    old_status = str(task.status.value if hasattr(task.status, "value") else task.status)

    new_status = status_data.get("status")
    if not new_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status is required")

    status_update = TaskStatusUpdate(status=new_status)

    try:
        updated_task = await task_service.update_task_status(
            task.id, status_update, current_user.id, commit=False
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


@router.put("/{task_id}/assign", response_model=TaskResponse)
@limiter.limit(RateLimits.TASK_UPDATE)
async def assign_task(
    request: Request,
    assign_data: dict,
    task: Task = Depends(get_async_authorized_task),
    db: AsyncSession = Depends(get_async_db),
    task_service: AsyncTaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Assign task to a user."""
    assignee_id = assign_data.get("assignee_id")
    if not assignee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee ID is required"
        )

    try:
        assignee_uuid = uuid.UUID(assignee_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid assignee ID format"
        )

    task_assign = TaskAssign(assignee_id=assignee_uuid)

    try:
        updated_task = await task_service.assign_task(
            task.id, task_assign, current_user.id, commit=False
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
