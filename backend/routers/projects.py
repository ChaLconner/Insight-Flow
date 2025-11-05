"""
Project management router for CRUD operations.
"""
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from schemas.project import ProjectResponse, ProjectCreate, ProjectUpdate, ProjectWithMembers, ProjectMemberResponse, ProjectMemberCreate
from schemas.user import UserResponse
from models.project import Project, ProjectMember
from models.user import User
from models.task import Task
from services.project_service import ProjectService
from database import get_db
from routers.auth import get_current_active_user
import uuid

router = APIRouter(prefix="/projects", tags=["project management"])

@router.get("/test")
def test_endpoint(db: Session = Depends(get_db)) -> Any:
    """Test endpoint to verify database connection."""
    try:
        # Simple database query to test connection
        from sqlalchemy import text
        result = db.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        return {"status": "success", "message": "Database connection working", "result": row[0] if row else None}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}

@router.get("/simple")
def simple_test() -> Any:
    """Simple test endpoint without database or auth."""
    return {"status": "success", "message": "Simple endpoint working"}

@router.get("/auth-test")
def auth_test(request: Request) -> Any:
    """Test endpoint that only checks token format."""
    auth_header = request.headers.get("authorization")
    print(f"auth_test: Received auth header: {auth_header}")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        print(f"auth_test: Extracted token: {token[:20]}...")
        return {"status": "success", "message": "Auth test endpoint working", "token_received": token[:20] + "..."}
    else:
        return {"status": "error", "message": "No valid Authorization header found"}

@router.get("/", response_model=List[ProjectResponse])
def read_projects(
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
    print(f"API: read_projects called by user {current_user.id} with params: skip={skip}, limit={limit}, user_projects_only={user_projects_only}")
    
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
        
        # Get project members with user data
        members = db.query(ProjectMember).join(User).filter(ProjectMember.project_id == project.id).all()
        
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
    print(f"API: read_projects completed in {end_time - start_time:.2f} seconds, returned {len(project_responses)} projects")
    
    return project_responses


@router.post("/", response_model=ProjectResponse)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new project.
    """
    project_service = ProjectService(db)
    try:
        project = project_service.create_project(project_data, current_user.id)
        
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
        
        # Get project members with user data
        members = db.query(ProjectMember).join(User).filter(ProjectMember.project_id == project.id).all()
        
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{project_id}", response_model=ProjectWithMembers)
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
    
    print(f"read_project: Called with project_id={project_id}, user_id={current_user.id}")
    
    project_service = ProjectService(db)
    
    # Check if user is a member of project
    try:
        project_uuid = uuid.UUID(project_id)
        print(f"read_project: Successfully parsed UUID: {project_uuid}")
    except ValueError as e:
        print(f"read_project: Invalid UUID format: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Check if user is owner or member
    try:
        project = project_service.get_project_by_id(project_uuid)
        print(f"read_project: Retrieved project: {project}")
    except Exception as e:
        print(f"read_project: Error getting project: {e}")
        print(f"read_project: Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving project"
        )
    
    if not project:
        print(f"read_project: Project not found for UUID: {project_uuid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
        
    if project.owner_id != current_user.id:
        try:
            is_member = project_service.is_project_member(project_uuid, current_user.id)
            print(f"read_project: User membership check result: {is_member}")
        except Exception as e:
            print(f"read_project: Error checking membership: {e}")
            print(f"read_project: Full traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error checking project membership"
            )
            
        if not is_member:
            print(f"read_project: User {current_user.id} is not a member of project {project_uuid}")
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
    
    # Get project members with user data
    members = db.query(ProjectMember).join(User).filter(ProjectMember.project_id == project_uuid).all()
    
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
        
        print(f"read_project: Successfully created response for project {project_uuid}")
        return project_response
        
    except Exception as e:
        print(f"read_project: Error creating project response: {e}")
        print(f"read_project: Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating project response"
        )

@router.put("/{project_id}", response_model=ProjectResponse)
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

@router.delete("/{project_id}")
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
        print(f"Unexpected error in delete_project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the project"
        )

@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
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
    
    members = db.query(ProjectMember).join(User).filter(ProjectMember.project_id == uuid.UUID(project_id)).all()
    
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

@router.post("/{project_id}/members", response_model=ProjectMemberResponse)
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
    project_service = ProjectService(db)
    
    try:
        member = project_service.add_project_member(uuid.UUID(project_id), member_data, current_user.id)
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{project_id}/members/{member_user_id}")
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

@router.put("/{project_id}/members/{member_user_id}/role")
def update_member_role(
    project_id: str,
    member_user_id: str,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update a member's role in a project.
    """
    import uuid
    project_service = ProjectService(db)
    
    try:
        updated_member = project_service.update_member_role(
            uuid.UUID(project_id),
            uuid.UUID(member_user_id),
            role_update.role,
            current_user.id
        )
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )