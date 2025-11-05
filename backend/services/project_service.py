"""
Project service layer for project management.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from models.project import Project, ProjectMember, MemberRole
from models.user import User
from models.task import Task
from schemas.project import ProjectCreate, ProjectUpdate, ProjectMemberCreate, ProjectMemberSummary
from schemas.user import UserResponse
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
        from sqlalchemy import func
        import time
        
        print(f"ProjectService: get_projects called with skip={skip}, limit={limit}, user_id={user_id}")
        start_time = time.time()
        
        # Build base query with filters
        query = self.db.query(Project)
        if user_id:
            # Get projects where user is owner or member
            query = query.filter(
                (Project.owner_id == user_id) |
                (Project.members.any(ProjectMember.user_id == user_id))
            )
        
        # Get projects first (simple query)
        projects = query.offset(skip).limit(limit).all()
        
        print(f"ProjectService: Retrieved {len(projects)} projects in {time.time() - start_time:.2f}s")
        
        if not projects:
            print("ProjectService: No projects found, returning empty list")
            return []
        
        # For now, skip complex statistics to isolate the timeout issue
        for project in projects:
            project.task_count = 0
            project.completed_tasks = 0
            project.member_count = 0
            project.member_summaries = []
        
        return projects
    
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
            
            # Add additional members if provided
            if project_data.members:
                for member_data in project_data.members:
                    # Check if user exists
                    user = self.db.query(User).filter(User.id == member_data.user_id).first()
                    if not user:
                        continue  # Skip invalid users
                    
                    # Check if user is already a member (including owner)
                    existing_member = self.db.query(ProjectMember).filter(
                        ProjectMember.project_id == db_project.id,
                        ProjectMember.user_id == member_data.user_id
                    ).first()
                    
                    if not existing_member:
                        new_member = ProjectMember(
                            project_id=db_project.id,
                            user_id=member_data.user_id,
                            role=member_data.role
                        )
                        self.db.add(new_member)
            
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
            # First delete all project members
            self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id).delete()
            
            # Then delete all tasks associated with the project
            self.db.query(Task).filter(Task.project_id == project_id).delete()
            
            # Finally delete the project
            self.db.delete(project)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            print(f"IntegrityError during project deletion: {e}")
            raise ValueError(f"Project deletion failed: {str(e)}")
        except Exception as e:
            self.db.rollback()
            print(f"Unexpected error during project deletion: {e}")
            raise ValueError(f"Project deletion failed: {str(e)}")
    
    def get_project_members(self, project_id: uuid.UUID) -> List[ProjectMember]:
        """Get all members of a project."""
        return self.db.query(ProjectMember).join(User).filter(ProjectMember.project_id == project_id).all()
    
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
            # Load member with user data
            member_with_user = self.db.query(ProjectMember).join(User).filter(ProjectMember.id == db_member.id).first()
            # Create a proper UserResponse object
            if member_with_user and member_with_user.user:
                member_with_user.user = UserResponse(
                    id=member_with_user.user.id,
                    email=member_with_user.user.email,
                    name=member_with_user.user.name,
                    avatar_url=member_with_user.user.avatar_url,
                    is_active=member_with_user.user.is_active,
                    created_at=member_with_user.user.created_at,
                    updated_at=member_with_user.user.updated_at
                )
            return member_with_user
            
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
        
        # Cannot remove owner
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
            # Load member with user data
            member_with_user = self.db.query(ProjectMember).join(User).filter(ProjectMember.id == member.id).first()
            # Create a proper UserResponse object
            if member_with_user and member_with_user.user:
                member_with_user.user = UserResponse(
                    id=member_with_user.user.id,
                    email=member_with_user.user.email,
                    name=member_with_user.user.name,
                    avatar_url=member_with_user.user.avatar_url,
                    is_active=member_with_user.user.is_active,
                    created_at=member_with_user.user.created_at,
                    updated_at=member_with_user.user.updated_at
                )
            return member_with_user
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Failed to update member role")
    
    def is_project_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is a member of project."""
        return self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first() is not None
    
    def is_project_admin(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is owner or admin of project."""
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