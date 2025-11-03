"""
Project service layer for project management.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.project import Project, ProjectMember, MemberRole
from models.user import User
from schemas.project import ProjectCreate, ProjectUpdate, ProjectMemberCreate
import uuid

class ProjectService:
    """Service class for project operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_project_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        """Get project by ID."""
        return self.db.query(Project).filter(Project.id == project_id).first()
    
    def get_projects(self, skip: int = 0, limit: int = 100, user_id: Optional[uuid.UUID] = None) -> List[Project]:
        """Get projects with pagination, optionally filtered by user."""
        query = self.db.query(Project)
        if user_id:
            # Get projects where user is owner or member
            query = query.filter(
                (Project.owner_id == user_id) |
                (Project.members.any(user_id=user_id))
            )
        return query.offset(skip).limit(limit).all()
    
    def create_project(self, project_data: ProjectCreate, owner_id: uuid.UUID) -> Project:
        """Create a new project."""
        try:
            db_project = Project(
                name=project_data.name,
                description=project_data.description,
                owner_id=owner_id
            )
            
            self.db.add(db_project)
            self.db.commit()
            self.db.refresh(db_project)
            
            # Add owner as project member with OWNER role
            owner_member = ProjectMember(
                project_id=db_project.id,
                user_id=owner_id,
                role=MemberRole.OWNER.value
            )
            self.db.add(owner_member)
            self.db.commit()
            
            return db_project
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Project creation failed")
    
    def update_project(self, project_id: uuid.UUID, project_data: ProjectUpdate, user_id: uuid.UUID) -> Project:
        """Update project information."""
        project = self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Check if user is owner or admin
        if not self.is_project_admin(project_id, user_id):
            raise ValueError("Only project owners and admins can update projects")
        
        # Update fields if provided
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.description is not None:
            project.description = project_data.description
        if project_data.is_active is not None:
            project.is_active = project_data.is_active
        
        try:
            self.db.commit()
            self.db.refresh(project)
            return project
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Project update failed")
    
    def delete_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a project."""
        project = self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Only owner can delete project
        if project.owner_id != user_id:
            raise ValueError("Only project owners can delete projects")
        
        try:
            self.db.delete(project)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Project deletion failed")
    
    def get_project_members(self, project_id: uuid.UUID) -> List[ProjectMember]:
        """Get all members of a project."""
        return self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    
    def add_project_member(self, project_id: uuid.UUID, member_data: ProjectMemberCreate, user_id: uuid.UUID) -> ProjectMember:
        """Add a member to a project."""
        project = self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Check if user is owner or admin
        if not self.is_project_admin(project_id, user_id):
            raise ValueError("Only project owners and admins can add members")
        
        # Check if user is already a member
        existing_member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_data.user_id
        ).first()
        
        if existing_member:
            raise ValueError("User is already a project member")
        
        try:
            db_member = ProjectMember(
                project_id=project_id,
                user_id=member_data.user_id,
                role=member_data.role
            )
            
            self.db.add(db_member)
            self.db.commit()
            self.db.refresh(db_member)
            return db_member
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Failed to add project member")
    
    def remove_project_member(self, project_id: uuid.UUID, member_user_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Remove a member from a project."""
        project = self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Check if user is owner or admin
        if not self.is_project_admin(project_id, user_id):
            raise ValueError("Only project owners and admins can remove members")
        
        # Cannot remove the owner
        if project.owner_id == member_user_id:
            raise ValueError("Cannot remove project owner")
        
        member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_user_id
        ).first()
        
        if not member:
            raise ValueError("Member not found")
        
        try:
            self.db.delete(member)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Failed to remove project member")
    
    def update_member_role(self, project_id: uuid.UUID, member_user_id: uuid.UUID, new_role: str, user_id: uuid.UUID) -> ProjectMember:
        """Update a member's role in a project."""
        project = self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Only owner can change roles
        if project.owner_id != user_id:
            raise ValueError("Only project owners can change member roles")
        
        # Cannot change owner's role
        if project.owner_id == member_user_id:
            raise ValueError("Cannot change owner's role")
        
        member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_user_id
        ).first()
        
        if not member:
            raise ValueError("Member not found")
        
        try:
            member.role = new_role
            self.db.commit()
            self.db.refresh(member)
            return member
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Failed to update member role")
    
    def is_project_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is a member of the project."""
        return self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first() is not None
    
    def is_project_admin(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is owner or admin of the project."""
        project = self.get_project_by_id(project_id)
        if not project:
            return False
        
        # Owner is always admin
        if project.owner_id == user_id:
            return True
        
        # Check if user is admin member
        member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.role.in_([MemberRole.OWNER.value, MemberRole.ADMIN.value])
        ).first()
        
        return member is not None