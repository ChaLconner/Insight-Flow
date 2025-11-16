from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import get_current_active_user
from models.user import User
from models.project import Project
from services.project_service import ProjectService
import uuid

def get_project_member(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    project = db.query(Project).filter(Project.id == project_uuid).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if user is owner
    if project.owner_id == current_user.id:
        return project_uuid
    
    # Check if user is a member
    project_service = ProjectService(db)
    is_member = project_service.is_project_member(project_uuid, current_user.id)
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    return project_uuid