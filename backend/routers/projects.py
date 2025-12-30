"""
Project management router for CRUD operations.
Refactored for Async operations with proper Dependency Injection.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from async_dependencies import require_project_admin, require_project_member, require_project_owner
from dependencies.services import get_notification_service, get_project_service
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
from services.async_notification_trigger_service import AsyncNotificationTriggerService
from services.async_project_service import AsyncProjectService
from utils.logger import setup_logger
from utils.response_helpers import (
    build_project_member_response,
    build_project_response,
    build_project_with_members_response,
)

logger = setup_logger("projects_router")

router = APIRouter(prefix="", tags=["project management"])


class RoleUpdate(BaseModel):
    """Schema for role update requests."""

    role: str


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
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
async def read_projects_list(
    skip: int = 0,
    limit: int = 100,
    user_projects_only: bool = Query(False),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Retrieve projects with pagination."""
    try:
        results = await project_service.get_projects_with_stats(
            skip=skip, limit=limit, user_id=current_user.id
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
async def update_project(
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
async def delete_project(
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
) -> Any:
    """Get all members of a project."""
    members = await project_service.get_project_members(project.id)

    return [ProjectMemberResponse.model_validate(build_project_member_response(m)) for m in members]


@router.post("/projects/{project_id}/members", response_model=ProjectMemberResponse)
async def add_project_member(
    project_id: str,
    member_data: ProjectMemberCreate,
    project_service: AsyncProjectService = Depends(get_project_service),
    notification_service: AsyncNotificationTriggerService = Depends(get_notification_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Add a member to a project."""
    try:
        pid = uuid.UUID(project_id)
        member = await project_service.add_project_member(pid, member_data, current_user.id)

        # Send notification
        project = await project_service.get_project_by_id(pid)
        if project and member.user:
            await notification_service.notify_project_member_added(
                new_member=member.user,
                project_id=pid,
                project_name=project.name,
                role=member.role,
                inviter=current_user,
            )

        return ProjectMemberResponse.model_validate(build_project_member_response(member))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding member: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add member")


@router.delete("/projects/{project_id}/members/{member_user_id}")
async def remove_project_member(
    member_user_id: str,
    project: Project = Depends(require_project_admin),
    project_service: AsyncProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Remove a member."""
    try:
        await project_service.remove_project_member(
            project.id, uuid.UUID(member_user_id), current_user.id
        )
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
