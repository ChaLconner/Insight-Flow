"""
Project management router for CRUD operations.
"""
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload
from schemas.project import ProjectResponse, ProjectCreate, ProjectUpdate, ProjectWithMembers, ProjectMemberResponse, ProjectMemberCreate
from schemas.user import UserResponse
from models.project import Project, ProjectMember
from models.user import User
from models.task import Task
from services.project_service import ProjectService
from database import get_db
from routers.auth import get_current_active_user
from utils.logger import setup_logger
import uuid

logger = setup_logger("projects_router")

router = APIRouter(prefix="", tags=["project management"])

# IMPORTANT: POST route must come BEFORE GET routes to avoid conflicts
@router.post("/projects", response_model=ProjectResponse)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new project.
    """
    logger.debug(f"Received project data: {project_data}")
    logger.debug(f"Members in project data: {project_data.members}")
    logger.debug(f"Current user: {current_user.id} ({current_user.email})")
    
    project_service = ProjectService(db)
    try:
        project = project_service.create_project(project_data, current_user.id)
        logger.info(f"Project created successfully: {project.id}")
        
        # Add statistics to project response
        # Get task count
        task_count = db.query(func.count(Task.id)).filter(Task.project_id == project.id).scalar()
        # Get completed tasks count
        completed_tasks = db.query(func.count(Task.id)).filter(
            Task.project_id == project.id,
            Task.status == 'done'
        ).scalar()
        # Get member count
        member_count = db.query(func.count(ProjectMember.id)).filter(
            ProjectMember.project_id == project.id
        ).scalar()
        
        # Get project members with user data using joinedload for better performance
        members = db.query(ProjectMember).options(
            joinedload(ProjectMember.user)
        ).filter(ProjectMember.project_id == project.id).all()
        
        # Create member summaries
        member_summaries = []
        for member in members:
            member_summaries.append({
                "id": str(member.id),
                "user_id": str(member.user_id),
                "name": member.user.name,
                "email": member.user.email,
                "avatar_url": member.user.avatar_url,
                "role": member.role
            })
        
        logger.debug(f"Returning project response with {len(member_summaries)} members")
        
        # Return project with statistics
        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            owner_id=project.owner_id,
            is_active=project.is_active,
            created_at=project.created_at,
            updated_at=project.updated_at,
            task_count=task_count or 0,
            completed_tasks=completed_tasks or 0,
            member_count=member_count or 0,
            member_summaries=member_summaries
        )
    except ValueError as e:
        logger.warning(f"ValueError occurred: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )

@router.get("/projects", response_model=List[ProjectResponse])
def read_projects_list(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    user_projects_only: bool = Query(False, description="Filter to show only user's projects"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Retrieve projects with pagination.
    """
    import time
    start_time = time.time()
    
    # Debug logging for authentication
    auth_header = request.headers.get("authorization")
    logger.debug(f"Auth header present: {bool(auth_header)}")
    if auth_header:
        logger.debug(f"Auth header starts with Bearer: {auth_header.startswith('Bearer ')}")
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            logger.debug(f"Token length: {len(token)}")
            logger.debug(f"Token preview: {token[:20]}...")
    
    logger.debug(f"Called by user {current_user.id} with params: skip={skip}, limit={limit}, user_projects_only={user_projects_only}")
    
    project_service = ProjectService(db)
    user_id = current_user.id if user_projects_only else None
    projects = project_service.get_projects(skip=skip, limit=limit, user_id=user_id)
    
    # Convert Project objects to ProjectResponse schemas
    project_responses = []
    for project in projects:
        # Get task count
        task_count = db.query(func.count(Task.id)).filter(Task.project_id == project.id).scalar()
        # Get completed tasks count
        completed_tasks = db.query(func.count(Task.id)).filter(
            Task.project_id == project.id,
            Task.status == 'done'
        ).scalar()
        # Get member count
        member_count = db.query(func.count(ProjectMember.id)).filter(
            ProjectMember.project_id == project.id
        ).scalar()
        
        # Get project members with user data using joinedload for better performance
        members = db.query(ProjectMember).options(
            joinedload(ProjectMember.user)
        ).filter(ProjectMember.project_id == project.id).all()
        
        # Create member summaries
        member_summaries = []
        for member in members:
            member_summaries.append({
                "id": str(member.id),
                "user_id": str(member.user_id),
                "name": member.user.name,
                "email": member.user.email,
                "avatar_url": member.user.avatar_url,
                "role": member.role
            })
        
        # Create ProjectResponse
        project_response = ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            owner_id=project.owner_id,
            is_active=project.is_active,
            created_at=project.created_at,
            updated_at=project.updated_at,
            task_count=task_count or 0,
            completed_tasks=completed_tasks or 0,
            member_count=member_count or 0,
            member_summaries=member_summaries
        )
        project_responses.append(project_response)
    
    end_time = time.time()
    logger.info(f"Completed in {end_time - start_time:.2f} seconds, returned {len(project_responses)} projects")
    
    return project_responses

# Routes with project_id parameter must come AFTER / routes
@router.get("/projects/{project_id}", response_model=ProjectWithMembers)
def read_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get project by ID with members.
    """
    import uuid
    import traceback
    
    logger.debug(f"Called with project_id={project_id}, user_id={current_user.id}")
    logger.debug(f"Current user email: {current_user.email}")
    
    project_service = ProjectService(db)
    
    # Check if user is a member of project
    try:
        project_uuid = uuid.UUID(project_id)
        logger.debug(f"Successfully parsed UUID: {project_uuid}")
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Check if user is owner or member
    try:
        project = project_service.get_project_by_id(project_uuid)
        logger.debug(f"Retrieved project: {project}")
        if project:
            logger.debug(f"Project name: {project.name}")
            logger.debug(f"Project owner: {project.owner_id}")
            logger.debug(f"Current user: {current_user.id}")
            logger.debug(f"Is owner: {project.owner_id == current_user.id}")
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving project"
        )
    
    if not project:
        logger.warning(f"Project not found for UUID: {project_uuid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
        
    if project.owner_id != current_user.id:
        try:
            is_member = project_service.is_project_member(project_uuid, current_user.id)
            logger.debug(f"User membership check result: {is_member}")
        except Exception as e:
            logger.error(f"Error checking membership: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error checking project membership"
            )
            
        if not is_member:
            logger.warning(f"User {current_user.id} is not a member of project {project_uuid}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this project"
            )
    
    # Add statistics to project
    # Get task count
    task_count = db.query(func.count(Task.id)).filter(Task.project_id == project_uuid).scalar()
    # Get completed tasks count
    completed_tasks = db.query(func.count(Task.id)).filter(
        Task.project_id == project_uuid,
        Task.status == 'done'
    ).scalar()
    # Get member count
    member_count = db.query(func.count(ProjectMember.id)).filter(
        ProjectMember.project_id == project_uuid
    ).scalar()
    
    # Get project members with user data using joinedload for better performance
    members = db.query(ProjectMember).options(
        joinedload(ProjectMember.user)
    ).filter(ProjectMember.project_id == project_uuid).all()
    
    try:
        # Create response with members and statistics
        project_response = ProjectWithMembers(
            id=project.id,
            name=project.name,
            description=project.description,
            owner_id=project.owner_id,
            is_active=project.is_active,
            created_at=project.created_at,
            updated_at=project.updated_at,
            task_count=task_count or 0,
            completed_tasks=completed_tasks or 0,
            member_count=member_count or 0,
            members=[
                ProjectMemberResponse(
                    id=member.id,
                    project_id=member.project_id,
                    user_id=member.user_id,
                    role=member.role,
                    joined_at=member.joined_at,
                    user=UserResponse(
                        id=member.user.id,
                        email=member.user.email,
                        name=member.user.name,
                        avatar_url=member.user.avatar_url,
                        is_active=member.user.is_active,
                        created_at=member.user.created_at,
                        updated_at=member.user.updated_at
                    )
                ) for member in members
            ]
        )
        
        logger.debug(f"Project {project_uuid} debug info:")
        logger.debug(f"  - Name: {project.name}")
        logger.debug(f"  - Task count: {task_count}")
        logger.debug(f"  - Completed tasks: {completed_tasks}")
        logger.debug(f"  - Member count: {member_count}")
        logger.debug(f"  - Is active: {project.is_active}")
        logger.debug(f"  - Created at: {project.created_at}")
        logger.debug(f"  - Updated at: {project.updated_at}")
        
        logger.debug(f"Successfully created response for project {project_uuid}")
        return project_response
        
    except Exception as e:
        logger.error(f"Error creating project response: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating project response"
        )

@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update project information.
    """
    import uuid
    project_service = ProjectService(db)
    

    try:
        project_uuid = uuid.UUID(project_id)
        updated_project = project_service.update_project(project_uuid, project_data, current_user.id)
        return updated_project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/projects/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete a project.
    """
    import uuid
    project_service = ProjectService(db)
    

    try:
        project_uuid = uuid.UUID(project_id)
        project_service.delete_project(project_uuid, current_user.id)
        return {"message": "Project deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in delete_project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting project"
        )

@router.get("/projects/{project_id}/members", response_model=List[ProjectMemberResponse])
def read_project_members(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get all members of a project.
    """
    import uuid
    project_service = ProjectService(db)
    
    # Check if user is a member of project
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Get project to check ownership
    project = project_service.get_project_by_id(project_uuid)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
        
    # Check if user is owner or member
    if project.owner_id != current_user.id:
        if not project_service.is_project_member(project_uuid, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this project"
            )
    
    members = db.query(ProjectMember).options(
        joinedload(ProjectMember.user)
    ).filter(ProjectMember.project_id == uuid.UUID(project_id)).all()
    
    # Ensure user data is included in response
    member_responses = []
    for member in members:
        member_responses.append(ProjectMemberResponse(
            id=member.id,
            project_id=member.project_id,
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
            user=UserResponse(
                id=member.user.id,
                email=member.user.email,
                name=member.user.name,
                avatar_url=member.user.avatar_url,
                is_active=member.user.is_active,
                created_at=member.user.created_at,
                updated_at=member.user.updated_at
            )
        ))
    
    return member_responses

@router.post("/projects/{project_id}/members", response_model=ProjectMemberResponse)
def add_project_member(
    project_id: str,
    member_data: ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Add a member to a project.
    """
    import uuid
    import traceback
    project_service = ProjectService(db)
    
    logger.debug(f"Called with project_id={project_id}, member_data={member_data}, current_user={current_user.email} (ID: {current_user.id})")
    
    try:
        member = project_service.add_project_member(uuid.UUID(project_id), member_data, current_user.id)
        logger.info(f"Successfully added member: {member}")
        # The service already returns member with user data
        return ProjectMemberResponse(
            id=member.id,
            project_id=member.project_id,
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
            user=UserResponse(
                id=member.user.id,
                email=member.user.email,
                name=member.user.name,
                avatar_url=member.user.avatar_url,
                is_active=member.user.is_active,
                created_at=member.user.created_at,
                updated_at=member.user.updated_at
            )
        )
    except ValueError as e:
        logger.warning(f"ValueError - {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error - {e}")
        logger.error(f"Full traceback - {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add project member: {str(e)}"
        )

@router.delete("/projects/{project_id}/members/{member_user_id}")
def remove_project_member(
    project_id: str,
    member_user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Remove a member from a project.
    """
    import uuid
    project_service = ProjectService(db)
    

    try:
        project_service.remove_project_member(uuid.UUID(project_id), uuid.UUID(member_user_id), current_user.id)
        return {"message": "Member removed successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

from pydantic import BaseModel

class RoleUpdate(BaseModel):
    role: str

@router.put("/projects/{project_id}/members/{member_user_id}/role")
def update_member_role(
    project_id: str,
    member_user_id: str,
    role_update: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update a member's role in a project.
    """
    import uuid
    project_service = ProjectService(db)
    
    # Add detailed logging for debugging
    logger.info(f"[DEBUG] update_member_role called:")
    logger.info(f"[DEBUG] - project_id: {project_id}")
    logger.info(f"[DEBUG] - member_user_id: {member_user_id}")
    logger.info(f"[DEBUG] - role_update: {role_update}")
    logger.info(f"[DEBUG] - current_user: {current_user.id} ({current_user.email})")
    logger.info(f"[DEBUG] - request headers: {dict(request.headers)}")
    logger.info(f"[DEBUG] - request origin: {request.headers.get('origin')}")
    logger.info(f"[DEBUG] - request method: {request.method}")
    
    try:
        # Validate role before passing to service
        valid_roles = ['admin', 'member', 'owner']
        if role_update.role not in valid_roles:
            logger.error(f"[DEBUG] Invalid role: {role_update.role}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role_update.role}. Valid roles are: {', '.join(valid_roles)}"
            )
        
        logger.info(f"[DEBUG] Calling project_service.update_member_role...")
        updated_member = project_service.update_member_role(
            uuid.UUID(project_id),
            uuid.UUID(member_user_id),
            role_update.role,
            current_user.id
        )
        logger.info(f"[DEBUG] Successfully updated member role: {updated_member}")
        
        # The service already returns member with user data
        return ProjectMemberResponse(
            id=updated_member.id,
            project_id=updated_member.project_id,
            user_id=updated_member.user_id,
            role=updated_member.role,
            joined_at=updated_member.joined_at,
            user=UserResponse(
                id=updated_member.user.id,
                email=updated_member.user.email,
                name=updated_member.user.name,
                avatar_url=updated_member.user.avatar_url,
                is_active=updated_member.user.is_active,
                created_at=updated_member.user.created_at,
                updated_at=updated_member.user.updated_at
            )
        )
    except ValueError as e:
        logger.error(f"[DEBUG] ValueError in update_member_role: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"[DEBUG] Unexpected error in update_member_role: {e}")
        import traceback
        logger.error(f"[DEBUG] Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update member role: {str(e)}"
        )
