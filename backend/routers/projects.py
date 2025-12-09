"""
Project management router for CRUD operations.
"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String
from sqlalchemy.orm import joinedload
from schemas.project import ProjectResponse, ProjectCreate, ProjectUpdate, ProjectWithMembers, ProjectMemberResponse, ProjectMemberCreate
from schemas.user import UserResponse
from models.project import ProjectMember
from models.user import User
from models.task import Task
from models.task import TaskStatus
from models.task_history import TaskHistory
from datetime import datetime, timedelta, timezone
from services.project_service import ProjectService
from services.task_service import TaskService
from schemas.task import TaskResponse, TaskCreate, TaskUpdate, TaskWithDetails, TaskStatusUpdate, TaskAssign, TaskListResponse
from database import get_db
from routers.auth import get_current_active_user
from utils.logger import setup_logger
from utils.validators import validate_uuid
from dependencies import require_project_admin, require_project_member, require_project_owner, ProjectPermission
from models.project import Project

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
            cast(Task.status, String) == TaskStatus.DONE.value
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
        
        # Return project with statistics - use model_validate for proper conversion
        return ProjectResponse.model_validate({
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'owner_id': project.owner_id,
            'is_active': project.is_active,
            'created_at': project.created_at,
            'updated_at': project.updated_at,
            'task_count': task_count or 0,
            'completed_tasks': completed_tasks or 0,
            'member_count': member_count or 0,
            'member_summaries': member_summaries
        })
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
    
    # Always filter by user_id to ensure users only see projects they have access to
    user_id = current_user.id
    
    # Use optimized service method
    projects_with_stats = project_service.get_projects_with_stats(skip=skip, limit=limit, user_id=user_id)
    
    # Convert results to ProjectResponse schemas
    project_responses = []
    for item in projects_with_stats:
        project = item['project']
        members = item['members']
        
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
        project_response = ProjectResponse.model_validate({
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'owner_id': project.owner_id,
            'is_active': project.is_active,
            'created_at': project.created_at,
            'updated_at': project.updated_at,
            'task_count': item['task_count'],
            'completed_tasks': item['completed_tasks'],
            'overdue_tasks': item['overdue_tasks'],
            'recent_activity': item['recent_activity'],
            'member_count': item['member_count'],
            'member_summaries': member_summaries
        })
        project_responses.append(project_response)
    
    end_time = time.time()
    logger.info(f"Completed in {end_time - start_time:.2f} seconds, returned {len(project_responses)} projects")
    
    return project_responses

# Routes with project_id parameter must come AFTER / routes
@router.get("/projects/{project_id}", response_model=ProjectWithMembers)
def read_project(
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get project by ID with members.
    """
    import uuid
    import traceback
    
    logger.debug(f"Called with project_id={project.id}, user_id={current_user.id}")
    logger.debug(f"Current user email: {current_user.email}")
    
    project_service = ProjectService(db)
    
    # Get project with details (optimized single query)
    project_details = project_service.get_project_with_details(project.id)
    
    if not project_details:
        logger.warning(f"Project not found for UUID: {project.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Permission check already done by dependency
    # project = project_details['project']
    
    members = project_details['members']
    
    try:
        # Create detailed member responses
        member_responses = [
            ProjectMemberResponse.model_validate({
                'id': member.id,
                'project_id': member.project_id,
                'user_id': member.user_id,
                'role': member.role,
                'joined_at': member.joined_at,
                'user': {
                    'id': member.user.id,
                    'email': member.user.email,
                    'name': member.user.name,
                    'avatar_url': member.user.avatar_url,
                    'is_active': member.user.is_active,
                    'role': member.user.role or "user",
                    'created_at': member.user.created_at,
                    'updated_at': member.user.updated_at
                }
            }) for member in members
        ]
        
        # Create member summaries (optional but good for consistency)
        member_summaries = [
            {
                'id': member.id,
                'user_id': member.user_id,
                'name': member.user.name,
                'email': member.user.email,
                'avatar': member.user.avatar_url,
                'role': member.role
            } for member in members
        ]

        # Create response with members and statistics
        project_response = ProjectWithMembers.model_validate({
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'owner_id': project.owner_id,
            'is_active': project.is_active,
            'created_at': project.created_at,
            'updated_at': project.updated_at,
            'task_count': project_details['task_count'],
            'completed_tasks': project_details['completed_tasks'],
            'overdue_tasks': project_details['overdue_tasks'],
            'recent_activity': project_details['recent_activity'],
            'member_count': project_details['member_count'],
            'members': member_responses,
            'member_summaries': member_summaries
        })
        
        return project_response
        
    except Exception as e:
        logger.error(f"Error creating project response: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating project response"
        )

@router.put("/projects/{project_id}", response_model=ProjectWithMembers)
def update_project(
    project_data: ProjectUpdate,
    project: Project = Depends(require_project_admin),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update project information.
    """
    import uuid
    import traceback
    
    logger.debug(f"Updating project {project.id} with data: {project_data}")
    
    project_service = ProjectService(db)
    
    try:
        # Update project
        updated_project = project_service.update_project(project.id, project_data, current_user.id)
        
        # Get full details for response
        project_details = project_service.get_project_with_details(updated_project.id)
        
        if not project_details:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found after update"
            )
            
        members = project_details['members']
        
        # Create detailed member responses
        member_responses = [
            ProjectMemberResponse.model_validate({
                'id': member.id,
                'project_id': member.project_id,
                'user_id': member.user_id,
                'role': member.role,
                'joined_at': member.joined_at,
                'user': {
                    'id': member.user.id,
                    'email': member.user.email,
                    'name': member.user.name,
                    'avatar_url': member.user.avatar_url,
                    'is_active': member.user.is_active,
                    'role': member.user.role or "user",
                    'created_at': member.user.created_at,
                    'updated_at': member.user.updated_at
                }
            }) for member in members
        ]
        
        # Create member summaries
        member_summaries = [
            {
                'id': member.id,
                'user_id': member.user_id,
                'name': member.user.name,
                'email': member.user.email,
                'avatar': member.user.avatar_url,
                'role': member.role
            } for member in members
        ]

        # Create response
        project_response = ProjectWithMembers.model_validate({
            'id': updated_project.id,
            'name': updated_project.name,
            'description': updated_project.description,
            'owner_id': updated_project.owner_id,
            'is_active': updated_project.is_active,
            'created_at': updated_project.created_at,
            'updated_at': updated_project.updated_at,
            'task_count': project_details['task_count'],
            'completed_tasks': project_details['completed_tasks'],
            'overdue_tasks': project_details['overdue_tasks'],
            'recent_activity': project_details['recent_activity'],
            'member_count': project_details['member_count'],
            'members': member_responses,
            'member_summaries': member_summaries
        })
        
        return project_response
        
    except ValueError as e:
        logger.error(f"ValueError updating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating project: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )

@router.delete("/projects/{project_id}")
def delete_project(
    project: Project = Depends(require_project_owner),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete a project.
    """
    import uuid
    project_service = ProjectService(db)
    project_service.delete_project(project.id, current_user.id)
    return {"message": "Project deleted successfully"}

@router.get("/projects/{project_id}/members", response_model=List[ProjectMemberResponse])
def read_project_members(
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get all members of a project.
    """
    import uuid
    # Check if user is a member of project
    # Permission check already done by dependency
    
    members = db.query(ProjectMember).options(
        joinedload(ProjectMember.user)
    ).filter(ProjectMember.project_id == project.id).all()
    
    # Ensure user data is included in response
    member_responses = []
    for member in members:
        member_responses.append(ProjectMemberResponse.model_validate({
            'id': member.id,
            'project_id': member.project_id,
            'user_id': member.user_id,
            'role': member.role,
            'joined_at': member.joined_at,
            'user': {
                'id': member.user.id,
                'email': member.user.email,
                'name': member.user.name,
                'avatar_url': member.user.avatar_url,
                'is_active': member.user.is_active,
                'role': member.user.role or "user",
                'created_at': member.user.created_at,
                'updated_at': member.user.updated_at
            }
        }))
    
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
        return ProjectMemberResponse.model_validate({
            'id': member.id,
            'project_id': member.project_id,
            'user_id': member.user_id,
            'role': member.role,
            'joined_at': member.joined_at,
            'user': {
                'id': member.user.id,
                'email': member.user.email,
                'name': member.user.name,
                'avatar_url': member.user.avatar_url,
                'is_active': member.user.is_active,
                'role': member.user.role or "user",
                'created_at': member.user.created_at,
                'updated_at': member.user.updated_at
            }
        })
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
    member_user_id: str,
    project: Project = Depends(require_project_admin),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Remove a member from a project.
    """
    import uuid
    project_service = ProjectService(db)
    project_service.remove_project_member(project.id, uuid.UUID(member_user_id), current_user.id)
    return {"message": "Member removed successfully"}

from pydantic import BaseModel

class RoleUpdate(BaseModel):
    role: str

@router.put("/projects/{project_id}/members/{member_user_id}/role")
def update_member_role(
    member_user_id: str,
    role_update: RoleUpdate,
    request: Request,
    project: Project = Depends(require_project_owner),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update a member's role in a project.
    """
    import uuid
    project_service = ProjectService(db)
    
    # Add detailed logging for debugging
    logger.info(f"update_member_role called:")
    logger.info(f"- project_id: {project.id}")
    logger.info(f"- member_user_id: {member_user_id}")
    logger.info(f"- role_update: {role_update}")
    logger.info(f"- current_user: {current_user.id} ({current_user.email})")
    logger.info(f"- request headers: {dict(request.headers)}")
    logger.info(f"- request origin: {request.headers.get('origin')}")
    logger.info(f"- request method: {request.method}")
    
    try:
        # Validate role before passing to service
        valid_roles = ['admin', 'member', 'owner']
        if role_update.role not in valid_roles:
            logger.error(f"Invalid role: {role_update.role}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role_update.role}. Valid roles are: {', '.join(valid_roles)}"
            )
        
        logger.info(f"Calling project_service.update_member_role...")
        updated_member = project_service.update_member_role(
            project.id,
            uuid.UUID(member_user_id),
            role_update.role,
            current_user.id
        )
        logger.info(f"Successfully updated member role: {updated_member}")
        
        # The service already returns member with user data
        return ProjectMemberResponse.model_validate({
            'id': updated_member.id,
            'project_id': updated_member.project_id,
            'user_id': updated_member.user_id,
            'role': updated_member.role,
            'joined_at': updated_member.joined_at,
            'user': {
                'id': updated_member.user.id,
                'email': updated_member.user.email,
                'name': updated_member.user.name,
                'avatar_url': updated_member.user.avatar_url,
                'is_active': updated_member.user.is_active,
                'role': updated_member.user.role or "user",
                'created_at': updated_member.user.created_at,
                'updated_at': updated_member.user.updated_at
            }
        })
    except ValueError as e:
        logger.error(f"ValueError in update_member_role: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in update_member_role: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update member role: {str(e)}"
        )

# ===========================================
# Task Management Endpoints have been moved to
# routers/project_tasks.py for better maintainability
# ===========================================
