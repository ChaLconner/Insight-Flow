from fastapi import Depends, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import get_current_active_user, get_current_user
from models.user import User
from models.project import Project, ProjectMember, MemberRole
from models.task import Task
import uuid
import services.project_service as project_service_module

class ProjectPermission:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        project_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> Project:
        try:
            p_uuid = uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid project ID")
            
        service = project_service_module.ProjectService(db)
        project = service.get_project_by_id(p_uuid)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project.owner_id == current_user.id:
            return project # Owners always have access

        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == p_uuid,
            ProjectMember.user_id == current_user.id
        ).first()

        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this project")

        if MemberRole(member.role).value not in self.allowed_roles:
             raise HTTPException(status_code=403, detail="Insufficient permissions")
             
        return project

# Pre-configured permissions
require_project_owner = ProjectPermission([MemberRole.OWNER.value])
require_project_admin = ProjectPermission([MemberRole.OWNER.value, MemberRole.ADMIN.value])
require_project_member = ProjectPermission([MemberRole.OWNER.value, MemberRole.ADMIN.value, MemberRole.MEMBER.value])

def get_authorized_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Task:
    """
    Dependency to get task by ID and ensure user has access (is project member).
    """
    try:
        t_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="Invalid task ID format"
        )
        
    task = db.query(Task).filter(Task.id == t_uuid).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Task not found"
        )

    # Check project membership using ProjectService
    project_service = project_service_module.ProjectService(db)
    if not project_service.is_project_member(task.project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
         
    return task