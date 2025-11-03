"""
Project management router for CRUD operations.
"""
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from schemas.project import ProjectResponse, ProjectCreate, ProjectUpdate, ProjectWithMembers, ProjectMemberResponse, ProjectMemberCreate
from models.project import Project, ProjectMember
from models.user import User
from services.project_service import ProjectService
from database import get_db
from routers.auth import get_current_active_user

router = APIRouter(prefix="/projects", tags=["project management"])

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
    project_service = ProjectService(db)
    user_id = current_user.id if user_projects_only else None
    projects = project_service.get_projects(skip=skip, limit=limit, user_id=user_id)
    return projects

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
        return project
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
    project_service = ProjectService(db)
    
    # Check if user is a member of the project
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    if not project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    try:
        project = project_service.get_project_by_id(uuid.UUID(project_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get project members
    try:
        project_uuid = uuid.UUID(project_id)
        members = project_service.get_project_members(project_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Create response with members
    project_response = ProjectWithMembers(
        id=project.id,
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
        is_active=project.is_active,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members=[
            ProjectMemberResponse(
                id=member.id,
                project_id=member.project_id,
                user_id=member.user_id,
                role=member.role,
                joined_at=member.joined_at,
                user=member.user
            ) for member in members
        ]
    )
    
    return project_response

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
    
    # Check if user is a member of the project
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    if not project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    members = project_service.get_project_members(uuid.UUID(project_id))
    return members

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
        return member
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

@router.put("/{project_id}/members/{member_user_id}/role")
def update_member_role(
    project_id: str,
    member_user_id: str,
    role: str,
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
            role, 
            current_user.id
        )
        return updated_member
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )