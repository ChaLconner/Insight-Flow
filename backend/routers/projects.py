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
# Task Management Endpoints (Project Context)
# ===========================================

@router.get("/projects/{project_id}/tasks", response_model=TaskListResponse)
def get_project_tasks(
    skip: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query(None, description="Sort order (asc/desc)"),
    search: Optional[str] = Query(None, description="Search term for title/description"),
    status: Optional[str] = Query(None, description="Filter by status"),
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get tasks for a specific project.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Add logging to validate sorting parameters
    logger.info(f"get_project_tasks called with params:")
    logger.info(f"project_id: {project.id}")
    logger.info(f"skip: {skip}")
    logger.info(f"limit: {limit}")
    logger.info(f"sort_by: {sort_by}")
    logger.info(f"sort_order: {sort_order}")
    logger.info(f"search: {search}")
    logger.info(f"status: {status}")
    logger.info(f"current_user: {current_user.id}")
    
    # Permission check already done by dependency
    
    try:
        logger.info(f"Calling task_service.get_project_tasks with sorting params")
        tasks, total = task_service.get_project_tasks(
            project.id, 
            skip=skip, 
            limit=limit, 
            sort_by=sort_by, 
            sort_order=sort_order,
            search=search,
            status=status
        )
        logger.info(f"Found {len(tasks)} tasks for project {project.id} (Total: {total})")
        logger.debug(f"Tasks data: {[{'id': str(t.id), 'title': t.title} for t in tasks]}")
        
        # Convert tasks to response format with full details
        items = []
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
                
            task_response = TaskWithDetails.model_validate({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': status_value,
                'project_id': task.project_id,
                'assignee_id': task.assignee_id,
                'created_by': task.created_by,
                'due_date': task.due_date,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'assignee': task.assignee,
                'creator': task.creator,
                'project': task.project,
                'priority': task.priority.value if hasattr(task.priority, 'value') else task.priority,
                'type': task.type.value if hasattr(task.type, 'value') else task.type
            })
            items.append(task_response)
        
        # Calculate pagination metadata
        page = (skip // limit) + 1 if limit > 0 else 1
        has_more = total > (skip + limit)
        
        return TaskListResponse(
            items=items,
            total=total,
            page=page,
            size=limit,
            has_more=has_more
        )
    except Exception as e:
        logger.error(f"Exception in get_project_tasks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project tasks: {str(e)}"
        )

@router.post("/projects/{project_id}/tasks", response_model=TaskResponse)
def create_task_for_project(
    task_data: TaskCreate,
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new task for a specific project.
    """
    import uuid
    task_service = TaskService(db)
    # Check if user is a member of project
    # Permission check already done by dependency
    
    logger.info(f"Task data: {task_data}")
    logger.info(f"Current user: {current_user.id}")
    
    # Override project_id in task_data to ensure consistency
    task_data.project_id = project.id
    
    
    try:
        task = task_service.create_task(task_data, current_user.id)
        logger.info(f"Task created successfully: {task.id}")
        
        # Log task response before returning
        logger.info(f"Preparing task response for ID: {task.id}")
        logger.info(f"Task response data: id={task.id}, title={task.title}, status={task.status}")
        
        # Create response explicitly to ensure all fields are included
        # Ensure status is returned as lowercase to match frontend expectations
        status_value = task.status.value if hasattr(task.status, 'value') else str(task.status)
        status_value = status_value.lower() if status_value else 'todo'
        
        task_response = TaskResponse.model_validate({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': status_value,
            'project_id': task.project_id,
            'assignee_id': task.assignee_id,
            'created_by': task.created_by,
            'due_date': task.due_date,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
            'priority': task.priority.value if hasattr(task.priority, 'value') else task.priority,
            'type': task.type.value if hasattr(task.type, 'value') else task.type
        })
        
        logger.info(f"DEBUG: TaskResponse created with ID: {task_response.id} (type: {type(task_response.id)})")
        
        return task_response
    except ValueError as e:
        logger.warning(f"Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

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
    
    # Validate UUIDs
    project_uuid = validate_uuid(project_id, "Invalid project ID format")
    task_uuid = validate_uuid(task_id, "Invalid task ID format")
    
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
        project=task.project,
        priority=task.priority.value if hasattr(task.priority, 'value') else task.priority,
        type=task.type.value if hasattr(task.type, 'value') else task.type
    )
    
    return task_response

@router.put("/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def update_project_task(
    task_id: str,
    task_data: TaskUpdate,
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task information by project ID and task ID.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Validate UUIDs
    task_uuid = validate_uuid(task_id, "Invalid task ID format")
    
    # Check if user is a member of project first
    # Permission check already done by dependency
    
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

@router.delete("/projects/{project_id}/tasks/{task_id}")
def delete_project_task(
    task_id: str,
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete a task by project ID and task ID.
    """
    import uuid
    task_service = TaskService(db)
    project_service = ProjectService(db)
    
    # Validate UUIDs
    task_uuid = validate_uuid(task_id, "Invalid task ID format")
    
    # Check if user is a member of project first
    # Permission check already done by dependency
    
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
    if task.project_id != project.id:
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

@router.put("/projects/{project_id}/tasks/{task_id}/status", response_model=TaskResponse)
def update_project_task_status(
    task_id: str,
    status_data: dict[str, str],
    project: Project = Depends(require_project_member),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update task status by project ID and task ID.
    """
    import uuid
    task_service = TaskService(db)
    
    # Validate UUIDs
    task_uuid = validate_uuid(task_id, "Invalid task ID format")
    
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
    # Permission check already done by dependency
    
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
    
    # Validate UUIDs
    project_uuid = validate_uuid(project_id, "Invalid project ID format")
    task_uuid = validate_uuid(task_id, "Invalid task ID format")
    
    # Extract assignee_id from request body
    assignee_id = assign_data.get("assignee_id")
    if not assignee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee ID is required"
        )
    
    # Create TaskAssign object
    assignee_uuid = validate_uuid(assignee_id, "Invalid assignee ID format")
    
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