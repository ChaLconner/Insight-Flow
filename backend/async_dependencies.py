"""
Async dependencies for Insight-Flow application.
This is the main dependencies module - all routers should import from here.

Note: This module uses lazy initialization to avoid circular dependency issues.
"""

import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _create_project_permission(allowed_roles: list[str]):
    """
    Factory function to create async project permission with proper dependency injection.
    This properly handles FastAPI's dependency analysis.
    """
    from database import get_async_db
    from dependencies.auth import get_current_active_user

    async def permission_check(
        project_id: str,
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ):
        from models.project import MemberRole, ProjectMember
        from services.async_project_service import AsyncProjectService

        try:
            p_uuid = uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid project ID")

        service = AsyncProjectService(db)
        project = await service.get_project_by_id(p_uuid)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if current_user.role == "admin":
            return project

        if project.owner_id == current_user.id:
            return project

        result = await db.execute(
            select(ProjectMember).filter(
                ProjectMember.project_id == p_uuid, ProjectMember.user_id == current_user.id
            )
        )
        member = result.scalars().first()

        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this project")

        if MemberRole(member.role).value not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return project

    return permission_check


def _create_task_authorization():
    """
    Factory function to create async task authorization with proper dependency injection.
    """
    from database import get_async_db
    from dependencies.auth import get_current_active_user

    async def authorize_task(
        task_id: str,
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ):
        from sqlalchemy.orm import selectinload

        from models.project import Project, ProjectMember
        from models.task import Task
        from services.async_task_service import AsyncTaskService

        try:
            t_uuid = uuid.UUID(task_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid task ID format")

        task_service = AsyncTaskService(db)
        task = await task_service.get_task_with_details(t_uuid)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if isinstance(task, dict):
            result = await db.execute(
                select(Task)
                .options(
                    selectinload(Task.assignee),
                    selectinload(Task.creator),
                    selectinload(Task.project),
                )
                .filter(Task.id == t_uuid)
            )
            task = result.scalars().first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

        if current_user.role == "admin":
            return task

        project_id = task.project_id

        result = await db.execute(
            select(Project).filter(Project.id == project_id, Project.owner_id == current_user.id)
        )
        if result.scalars().first():
            return task

        result = await db.execute(
            select(ProjectMember).filter(
                ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id
            )
        )
        if not result.scalars().first():
            raise HTTPException(status_code=403, detail="Not authorized to access this task")

        return task

    return authorize_task


# Lazy initialization of permission instances
_require_project_owner = None
_require_project_admin = None
_require_project_member = None
_get_async_authorized_task = None


def _ensure_initialized():
    """Initialize permission instances when first accessed."""
    global \
        _require_project_owner, \
        _require_project_admin, \
        _require_project_member, \
        _get_async_authorized_task

    if _require_project_owner is None:
        _require_project_owner = _create_project_permission(["owner"])
        _require_project_admin = _create_project_permission(["owner", "admin"])
        _require_project_member = _create_project_permission(["owner", "admin", "member"])
        _get_async_authorized_task = _create_task_authorization()


# Public interface as module-level callables
# These are accessed via __getattr__ for lazy initialization
def __getattr__(name):
    """Lazy attribute access for permission instances."""
    _ensure_initialized()

    if name == "require_project_owner":
        return _require_project_owner
    elif name == "require_project_admin":
        return _require_project_admin
    elif name == "require_project_member":
        return _require_project_member
    elif name in ("get_async_authorized_task", "get_authorized_task"):
        return _get_async_authorized_task

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [  # noqa: F822 - Names are dynamically provided by __getattr__
    "get_async_authorized_task",
    "get_authorized_task",
    "require_project_admin",
    "require_project_member",
    "require_project_owner",
]
