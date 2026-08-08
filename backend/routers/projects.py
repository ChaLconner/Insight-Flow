"""
Project management router for CRUD operations.
Refactored for Async operations with proper Dependency Injection.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from async_dependencies import require_project_admin, require_project_member, require_project_owner
from database import get_async_db
from dependencies.services import get_project_service
from models.project import Project
from models.user import User
from routers.auth import get_current_active_user
from schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithMembers,
)
from services.async_project_service import AsyncProjectService
from services.job_queue import enqueue_job
from utils.logger import setup_logger
from utils.response_helpers import (
    build_project_member_response,
    build_project_response,
    build_project_with_members_response,
)

logger = setup_logger("projects_router")

router = APIRouter(prefix="", tags=["project management"])

# Route-level rate limiting for project operations
from rate_limiter import RateLimits, limiter


class RoleUpdate(BaseModel):
    """Schema for role update requests."""

    role: str


@router.post("/projects", response_model=ProjectResponse)
@limiter.limit(RateLimits.PROJECT_CREATE)
async def create_project(
    request: Request,
    project_data: ProjectCreate,
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Create a new project."""
    logger.debug(f"Received project data: {project_data}")

    try:
        project = await project_service.create_project(project_data, current_user.id)

        # Fetch fresh details with helper
        project_details = await project_service.get_project_with_details(project.id)
        if not project_details:
            raise HTTPException(status_code=404, detail="Project not found")
        members = project_details["members"]

        return ProjectResponse.model_validate(
            build_project_response(project, project_details, members)
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create project"
        )


@router.get("/projects", response_model=list[ProjectResponse])
@limiter.limit(RateLimits.API_READ)
async def read_projects_list(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    status_filter: str | None = Query(None, alias="status"),
    sort_by: str = Query("newest"),
    user_projects_only: bool = Query(False),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Retrieve projects with pagination."""
    try:
        results = await project_service.get_projects_with_stats(
            skip=skip,
            limit=limit,
            user_id=current_user.id,
            user_projects_only=user_projects_only,
            search=search,
            status_filter=status_filter,
            sort_by=sort_by,
        )

        project_responses = []
        for item in results:
            project = item["project"]
            members = item["members"]

            response_data = build_project_response(project, item, members)
            project_responses.append(ProjectResponse.model_validate(response_data))

        return project_responses
    except Exception as e:
        logger.error(f"Error reading projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch projects")


@router.get("/projects/{project_id}", response_model=ProjectWithMembers)
async def read_project(
    project: Project = Depends(require_project_member),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get project by ID with members."""
    details = await project_service.get_project_with_details(project.id)
    if not details:
        raise HTTPException(status_code=404, detail="Project not found")

    members = details["members"]

    return ProjectWithMembers.model_validate(
        build_project_with_members_response(project, details, members)
    )


@router.put("/projects/{project_id}", response_model=ProjectWithMembers)
@limiter.limit(RateLimits.PROJECT_UPDATE)
async def update_project(
    request: Request,
    project_data: ProjectUpdate,
    project: Project = Depends(require_project_admin),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update project information."""
    try:
        updated_project = await project_service.update_project(
            project.id, project_data, current_user.id
        )

        # Return full details
        details = await project_service.get_project_with_details(updated_project.id)
        if not details:
            raise HTTPException(status_code=404, detail="Project not found")
        members = details["members"]

        return ProjectWithMembers.model_validate(
            build_project_with_members_response(updated_project, details, members)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update project")


@router.delete("/projects/{project_id}")
@limiter.limit(RateLimits.PROJECT_DELETE)
async def delete_project(
    request: Request,
    project: Project = Depends(require_project_owner),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Delete a project."""
    try:
        await project_service.delete_project(project.id, current_user.id)
        return {"message": "Project deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberResponse])
async def read_project_members(
    project: Project = Depends(require_project_member),
    project_service: AsyncProjectService = Depends(get_project_service),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> Any:
    """Get a bounded page of project members."""
    members = await project_service.get_project_members(project.id, offset=offset, limit=limit)

    return [ProjectMemberResponse.model_validate(build_project_member_response(m)) for m in members]


@router.post("/projects/{project_id}/members", response_model=ProjectMemberResponse)
@limiter.limit(RateLimits.PROJECT_MEMBERS)
async def add_project_member(
    request: Request,
    project_id: str,
    member_data: ProjectMemberCreate,
    db: AsyncSession = Depends(get_async_db),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Add a member to a project."""
    try:
        pid = uuid.UUID(project_id)
        member = await project_service.add_project_member(
            pid, member_data, current_user.id, commit=False
        )

        # Persist notification intent for the durable worker.
        project = await project_service.get_project_by_id(pid)
        if project:
            await enqueue_job(
                db,
                "notification.dispatch",
                {
                    "event": "project_member_added",
                    "member_id": str(member.user_id),
                    "project_id": str(pid),
                    "project_name": project.name,
                    "role": member.role,
                    "inviter_id": str(current_user.id),
                },
                idempotency_key=f"project-member-added:{pid}:{member.user_id}",
            )
        await db.commit()

        return ProjectMemberResponse.model_validate(build_project_member_response(member))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding member: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add member")


@router.delete("/projects/{project_id}/members/{member_user_id}")
@limiter.limit(RateLimits.PROJECT_MEMBERS)
async def remove_project_member(
    request: Request,
    member_user_id: str,
    project: Project = Depends(require_project_admin),
    db: AsyncSession = Depends(get_async_db),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Remove a member."""
    try:
        member_uuid = uuid.UUID(member_user_id)
        await project_service.remove_project_member(
            project.id, member_uuid, current_user.id, commit=False
        )

        await enqueue_job(
            db,
            "notification.dispatch",
            {
                "event": "project_member_removed",
                "member_id": str(member_uuid),
                "project_id": str(project.id),
                "project_name": project.name,
                "remover_id": str(current_user.id),
            },
            idempotency_key=f"project-member-removed:{project.id}:{member_uuid}",
        )
        await db.commit()
        return {"message": "Member removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}/members/{member_user_id}/role")
async def update_member_role(
    member_user_id: str,
    role_update: RoleUpdate,
    project: Project = Depends(require_project_owner),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update a member's role."""
    try:
        updated_member = await project_service.update_member_role(
            project.id, uuid.UUID(member_user_id), role_update.role, current_user.id
        )
        return ProjectMemberResponse.model_validate(build_project_member_response(updated_member))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update role")
