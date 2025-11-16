"""
Project service layer for project management.
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from models.project import Project, ProjectMember, MemberRole
from models.user import User
from models.task import Task
from schemas.project import ProjectCreate, ProjectUpdate, ProjectMemberCreate, ProjectMemberSummary
from schemas.user import UserResponse
import uuid
from utils.logger import logger

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
        
        logger.debug(f"get_projects called with skip={skip}, limit={limit}, user_id={user_id}")
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
        
        logger.debug(f"Retrieved {len(projects)} projects in {time.time() - start_time:.2f}s")
        
        if not projects:
            logger.debug("No projects found, returning empty list")
            return []
        
        # For now, skip complex statistics to isolate timeout issue
        for project in projects:
            project.task_count = 0
            project.completed_tasks = 0
            project.member_count = 0
            project.member_summaries = []
        
        return projects
    
    def create_project(self, project_data: ProjectCreate, owner_id: uuid.UUID) -> Project:
        """Create a new project."""
        logger.debug(f"Starting project creation with data: {project_data}, owner_id: {owner_id}")
        try:
            db_project = Project(
                name=project_data.name,
                description=project_data.description,
                owner_id=owner_id
            )
            
            self.db.add(db_project)
            self.db.flush()  # Get ID without committing
            logger.info(f"Project created with ID: {db_project.id}")
            
            # Add owner as project member with OWNER role
            owner_member = ProjectMember(
                project_id=db_project.id,
                user_id=owner_id,
                role=MemberRole.OWNER.value
            )
            self.db.add(owner_member)
            self.db.flush()  # Get member ID without committing
            logger.debug(f"Owner added as member with role: {MemberRole.OWNER.value}")
            
            # Add additional members if provided
            if project_data.members:
                logger.debug(f"Adding {len(project_data.members)} members to project {db_project.id}")
                for member_data in project_data.members:
                    logger.debug(f"Processing member data: {member_data}")
                    # Check if user exists - convert string UUID to UUID object
                    try:
                        user_uuid = uuid.UUID(str(member_data.user_id))
                        user = self.db.query(User).filter(User.id == user_uuid).first()
                    except ValueError:
                        logger.warning(f"Invalid UUID format for user_id: {member_data.user_id}, skipping")
                        continue
                    
                    if not user:
                        logger.warning(f"User {member_data.user_id} not found, skipping")
                        continue  # Skip invalid users
                    
                    # Check if user is already a member (including owner)
                    try:
                        user_uuid = uuid.UUID(str(member_data.user_id))
                        existing_member = self.db.query(ProjectMember).filter(
                            ProjectMember.project_id == db_project.id,
                            ProjectMember.user_id == user_uuid
                        ).first()
                    except ValueError:
                        logger.warning(f"Invalid UUID format for user_id: {member_data.user_id}, skipping member check")
                        continue
                    
                    if existing_member:
                        logger.warning(f"User {member_data.user_id} is already a member, skipping")
                        continue
                    
                    # Validate role and use enum value
                    role_value = member_data.role
                    if role_value == 'admin':
                        role_value = MemberRole.ADMIN.value
                    elif role_value == 'member':
                        role_value = MemberRole.MEMBER.value
                    
                    logger.debug(f"Adding member {user.email} with role {role_value}")
                    try:
                        user_uuid = uuid.UUID(str(member_data.user_id))
                        new_member = ProjectMember(
                            project_id=db_project.id,
                            user_id=user_uuid,
                            role=role_value
                        )
                    except ValueError:
                        logger.warning(f"Invalid UUID format for user_id: {member_data.user_id}, skipping member creation")
                        continue
                    self.db.add(new_member)
                    logger.debug(f"Added member to session")
            
            # Commit the transaction
            self.db.commit()
            self.db.refresh(db_project)
            logger.info(f"Project creation completed successfully")
            
            # Skip activity logging for now to focus on main issue
            # TODO: Fix activity logging enum issue
            logger.debug("Skipping activity logging due to enum issue")
            
            return db_project
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"IntegrityError occurred: {e}")
            raise ValueError(f"Project creation failed due to database constraint: {str(e)}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error occurred: {e}")
            raise ValueError(f"Project creation failed: {str(e)}")
    
    def update_project(self, project_id: uuid.UUID, project_data: ProjectUpdate, user_id: uuid.UUID) -> Project:
        """Update project information."""
        project = self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Check if user is owner or admin
        if not self.is_project_admin(project_id, user_id):
            raise ValueError("Only project owners and admins can update projects")
        
        # Track changes for activity logging
        changes = {}
        
        # Update fields if provided
        if project_data.name is not None:
            changes["name"] = project_data.name
            project.name = project_data.name
        if project_data.description is not None:
            changes["description"] = project_data.description
            project.description = project_data.description
        if project_data.is_active is not None:
            changes["is_active"] = project_data.is_active
            project.is_active = project_data.is_active
        
        try:
            self.db.commit()
            self.db.refresh(project)
            
            # Log activity if there were changes
            if changes:
                from services.task_history_service import TaskHistoryService
                task_history_service = TaskHistoryService(self.db)
                task_history_service.log_project_updated(
                    project_id=project_id,
                    updated_by=user_id,
                    changes=changes
                )
            
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
            
            # Then delete all tasks associated with project
            self.db.query(Task).filter(Task.project_id == project_id).delete()
            
            # Finally delete project
            self.db.delete(project)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"IntegrityError during project deletion: {e}")
            raise ValueError(f"Project deletion failed: {str(e)}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error during project deletion: {e}")
            raise ValueError(f"Project deletion failed: {str(e)}")
    
    def get_project_members(self, project_id: uuid.UUID) -> List[ProjectMember]:
        """Get all members of a project."""
        return self.db.query(ProjectMember).options(
            joinedload(ProjectMember.user)
        ).filter(ProjectMember.project_id == project_id).all()
    
    def add_project_member(self, project_id: uuid.UUID, member_data: ProjectMemberCreate, user_id: uuid.UUID) -> ProjectMember:
        """Add a member to a project."""
        logger.debug(f"Called with project_id={project_id}, member_data={member_data}, user_id={user_id}")
        
        project = self.get_project_by_id(project_id)
        if not project:
            logger.warning(f"Project not found for ID {project_id}")
            raise ValueError("Project not found")
        
        logger.debug(f"Found project: {project.name}, owner: {project.owner_id}")
        
        # Check if user is owner or admin
        is_admin = self.is_project_admin(project_id, user_id)
        logger.debug(f"User {user_id} is admin: {is_admin}")
        
        if not is_admin:
            logger.warning(f"User {user_id} is not admin of project {project_id}")
            raise ValueError("Only project owners and admins can add members")
        
        # Check if user is already a member
        try:
            user_uuid = uuid.UUID(str(member_data.user_id))
            existing_member = self.db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_uuid
            ).first()
        except ValueError:
            print(f"add_project_member: Invalid UUID format for user_id: {member_data.user_id}")
            raise ValueError("Invalid user ID format")
        
        if existing_member:
            logger.warning(f"User {member_data.user_id} is already a member of project {project_id}")
            raise ValueError("User is already a project member")
        
        try:
            logger.debug(f"Creating new member with role {member_data.role}")
            
            # Validate role and use enum value
            role_value = member_data.role
            if role_value == 'admin':
                role_value = MemberRole.ADMIN.value
            elif role_value == 'member':
                role_value = MemberRole.MEMBER.value
            elif role_value == 'owner':
                role_value = MemberRole.OWNER.value
            
            try:
                user_uuid = uuid.UUID(str(member_data.user_id))
                db_member = ProjectMember(
                    project_id=project_id,
                    user_id=user_uuid,
                    role=role_value
                )
            except ValueError:
                logger.warning(f"Invalid UUID format for user_id: {member_data.user_id}")
                raise ValueError("Invalid user ID format")
            
            self.db.add(db_member)
            self.db.commit()
            self.db.refresh(db_member)
            logger.info(f"Successfully created member with ID {db_member.id}")
            
            # Log activity
            from services.task_history_service import TaskHistoryService
            task_history_service = TaskHistoryService(self.db)
            added_user = self.db.query(User).filter(User.id == member_data.user_id).first()
            if added_user:
                task_history_service.log_project_member_added(
                    project_id=project_id,
                    member_name=added_user.name,
                    added_by=user_id
                )
            
            # Load member with user data
            try:
                member_with_user = self.db.query(ProjectMember).options(
                    joinedload(ProjectMember.user)
                ).filter(ProjectMember.id == db_member.id).first()
            except ValueError:
                logger.error(f"Error loading member with user data")
                raise ValueError("Error loading member data")
            
            logger.debug(f"Returning member with user: {member_with_user.user.email}")
            return member_with_user
            
        except IntegrityError as e:
            logger.error(f"IntegrityError - {e}")
            self.db.rollback()
            raise ValueError("Failed to add project member")
        except Exception as e:
            logger.error(f"Unexpected error - {e}")
            self.db.rollback()
            raise ValueError(f"Failed to add project member: {str(e)}")
    
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
            # Get user name for activity logging before deletion
            removed_user = self.db.query(User).filter(User.id == member_user_id).first()
            member_name = removed_user.name if removed_user else "Unknown User"
            
            self.db.delete(member)
            self.db.commit()
            
            # Log activity
            from services.task_history_service import TaskHistoryService
            task_history_service = TaskHistoryService(self.db)
            task_history_service.log_project_member_removed(
                project_id=project_id,
                member_name=member_name,
                removed_by=user_id
            )
            
            return True
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Failed to remove project member")
    
    def update_member_role(self, project_id: uuid.UUID, member_user_id: uuid.UUID, new_role: str, user_id: uuid.UUID) -> ProjectMember:
        """Update a member's role in a project."""
        logger.info(f"[DEBUG] update_member_role service called:")
        logger.info(f"[DEBUG] - project_id: {project_id}")
        logger.info(f"[DEBUG] - member_user_id: {member_user_id}")
        logger.info(f"[DEBUG] - new_role: {new_role}")
        logger.info(f"[DEBUG] - user_id: {user_id}")
        
        project = self.get_project_by_id(project_id)
        if not project:
            logger.error(f"[DEBUG] Project not found: {project_id}")
            raise ValueError("Project not found")
        
        logger.info(f"[DEBUG] Found project: {project.name}, owner: {project.owner_id}")
        
        # Only owner can change roles
        if project.owner_id != user_id:
            logger.error(f"[DEBUG] User {user_id} is not owner of project {project_id}")
            raise ValueError("Only project owners can change member roles")
        
        # Cannot change owner's role
        if project.owner_id == member_user_id:
            logger.error(f"[DEBUG] Attempting to change owner's role: {member_user_id}")
            raise ValueError("Cannot change owner's role")
        
        member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_user_id
        ).first()
        
        if not member:
            logger.error(f"[DEBUG] Member not found: {member_user_id} in project {project_id}")
            raise ValueError("Member not found")
        
        logger.info(f"[DEBUG] Found member: {member.id}, current role: {member.role}")
        
        try:
            # Get user name for activity logging
            member_user = self.db.query(User).filter(User.id == member_user_id).first()
            member_name = member_user.name if member_user else "Unknown User"
            
            # Validate role and use enum value
            role_value = new_role
            if role_value == 'admin':
                role_value = MemberRole.ADMIN.value
            elif role_value == 'member':
                role_value = MemberRole.MEMBER.value
            elif role_value == 'owner':
                role_value = MemberRole.OWNER.value
            else:
                logger.error(f"[DEBUG] Invalid role: {new_role}")
                raise ValueError(f"Invalid role: {new_role}")
            
            logger.info(f"[DEBUG] Updating role from {member.role} to {role_value}")
            member.role = role_value
            self.db.commit()
            self.db.refresh(member)
            logger.info(f"[DEBUG] Successfully updated role in database")
            
            # Log activity
            from services.task_history_service import TaskHistoryService
            task_history_service = TaskHistoryService(self.db)
            task_history_service.log_project_member_role_changed(
                project_id=project_id,
                member_name=member_name,
                new_role=new_role,
                changed_by=user_id
            )
            
            # Load member with user data
            member_with_user = self.db.query(ProjectMember).options(
                joinedload(ProjectMember.user)
            ).filter(ProjectMember.id == member.id).first()
            
            logger.info(f"[DEBUG] Returning updated member with user data")
            return member_with_user
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"[DEBUG] IntegrityError in update_member_role: {e}")
            raise ValueError("Failed to update member role")
        except Exception as e:
            self.db.rollback()
            logger.error(f"[DEBUG] Unexpected error in update_member_role: {e}")
            import traceback
            logger.error(f"[DEBUG] Full traceback: {traceback.format_exc()}")
            raise ValueError(f"Failed to update member role: {str(e)}")
    
    
    def is_project_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is a member of project."""
        logger.info(f"is_project_member: Checking if user {user_id} is member of project {project_id}")
        
        # First check if user is owner (owners are always members)
        project = self.get_project_by_id(project_id)
        logger.debug(f"Retrieved project: {project}")
        if project:
            logger.debug(f"Project owner: {project.owner_id}")
            logger.debug(f"Current user: {user_id}")
            logger.debug(f"Is owner: {project.owner_id == user_id}")
            
        if project and project.owner_id == user_id:
            logger.info(f"User {user_id} is owner of project {project_id}, returning True")
            return True
            
        # Then check if user is in project members table
        member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first()
        
        logger.debug(f"Member query result: {member}")
        result = member is not None
        logger.info(f"User {user_id} is member of project {project_id}: {result}")
        return result
    
    def is_project_admin(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is owner or admin of project."""
        logger.debug(f"Checking if user {user_id} is admin of project {project_id}")
        
        project = self.get_project_by_id(project_id)
        if not project:
            logger.warning(f"Project {project_id} not found")
            return False
        
        logger.debug(f"Project {project_id} found, owner: {project.owner_id}")
        
        # Owner is always admin
        if project.owner_id == user_id:
            logger.debug(f"User {user_id} is owner of project {project_id}")
            return True
        
        # Check if user is admin member
        member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.role.in_([MemberRole.OWNER.value, MemberRole.ADMIN.value])
        ).first()
        
        logger.debug(f"Member query result: {member}")
        result = member is not None
        logger.debug(f"User {user_id} is admin of project {project_id}: {result}")
        return result