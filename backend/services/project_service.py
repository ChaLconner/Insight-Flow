"""
Project service layer for project management.
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from models.project import Project, ProjectMember, MemberRole
from models.user import User
from models.task import Task
from schemas.project import ProjectCreate, ProjectUpdate, ProjectMemberCreate, ProjectMemberSummary
from schemas.user import UserResponse
import uuid
from utils.logger import logger
from models.analytics import (
    ProjectAnalytics, UserProductivity, TaskTimeTracking, 
    ProjectMilestone, TaskDependency, TaskComment, 
    TaskAttachment, ProjectTagAssociation
)
from models.task_history import TaskHistory

class ProjectService:
    """Service class for project operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_project_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        """Get project by ID."""
        return self.db.query(Project).filter(Project.id == project_id).first()
    
    def get_projects(self, skip: int = 0, limit: int = 100, user_id: Optional[uuid.UUID] = None) -> List[Project]:
        """Get projects with pagination, optionally filtered by user."""
        import time
        from sqlalchemy import or_
        
        logger.debug(f"get_projects called with skip={skip}, limit={limit}, user_id={user_id}")
        start_time = time.time()
        
        # Build base query with filters
        query = self.db.query(Project)
        if user_id:
            # Get projects where user is owner or member
            query = query.filter(
                or_(
                    Project.owner_id == user_id,
                    Project.members.any(ProjectMember.user_id == user_id)
                )
            )
        
        # Get projects
        projects = query.offset(skip).limit(limit).all()
        
        logger.debug(f"Retrieved {len(projects)} projects in {time.time() - start_time:.2f}s")
        return projects

    def get_projects_with_stats(self, skip: int = 0, limit: int = 100, user_id: Optional[uuid.UUID] = None) -> List[dict]:
        """Get projects with aggregated statistics using optimized queries."""
        import time
        from sqlalchemy import or_, and_, case, distinct, cast, String
        from models.task import TaskStatus, Task
        from models.project import ProjectMember
        from models.task_history import TaskHistory
        from datetime import datetime, timedelta, timezone

        start_time = time.time()
        
        # Base query for projects
        projects_query = self.db.query(
            Project,
            func.count(distinct(Task.id)).label("task_count"),
            func.count(distinct(
                case(
                    (cast(Task.status, String) == TaskStatus.DONE.value, Task.id),
                    else_=None
                )
            )).label("completed_tasks"),
            func.count(distinct(
                case(
                    (and_(
                        cast(Task.status, String) != TaskStatus.DONE.value,
                        Task.due_date < datetime.now(timezone.utc)
                    ), Task.id),
                    else_=None
                )
            )).label("overdue_tasks"),
            func.count(distinct(ProjectMember.id)).label("member_count")
        ).outerjoin(
            Task, Task.project_id == Project.id
        ).outerjoin(
            ProjectMember, ProjectMember.project_id == Project.id
        )

        if user_id:
            # Filter projects where user is owner or member
            # Note: We need a subquery or distinct check for correct filtering with joins
            # But for simplicity and correctness with the group_by, we filter properly.
            # However, since we are doing outer joins, direct filtering on the main query might filter out rows.
            # The common pattern is to verify access first or use a subquery for the project IDs.
            
            # Efficient way: Get accessible project IDs first
            accessible_projects = self.db.query(Project.id).filter(
                or_(
                    Project.owner_id == user_id,
                    Project.members.any(ProjectMember.user_id == user_id)
                )
            )
            projects_query = projects_query.filter(Project.id.in_(accessible_projects))

        projects_query = projects_query.group_by(Project.id).offset(skip).limit(limit)
        
        results = projects_query.all()
        
        # Batch fetch members for all projects to avoid N+1 queries
        project_ids = [r[0].id for r in results]
        project_members_map = {}
        
        if project_ids:
            # Fetch members for these projects
            # We want to limit to 5 per project, but SQL window functions/limit per group is complex in ORM
            # For now, fetching all members for these page of projects and slicing in python is better than N queries
            # provided the member count isn't massive (thousands). 
            # Given pagination of projects (defaults to 100), this is safer.
            all_members = self.db.query(ProjectMember).options(
                selectinload(ProjectMember.user)
            ).filter(ProjectMember.project_id.in_(project_ids)).all()
            
            from collections import defaultdict
            members_by_project = defaultdict(list)
            for m in all_members:
                members_by_project[m.project_id].append(m)
            
            # Slice to 5 per project
            for pid, members in members_by_project.items():
                project_members_map[pid] = members[:5]
        
        formatted_results = []
        for project, task_count, completed_tasks, overdue_tasks, member_count in results:
            # Get members from map
            members = project_members_map.get(project.id, [])
            
            # Recent activity count (separate query for simplicity/speed vs complexity of another join)
            # This is still N+1 but much lighter than members. 
            # Optimizing this would require a grouped aggregation on TaskHistory which might be heavy.
            # Leaving as is for now unless activity log is huge.
            # Load recent activity counts map if not loaded
            if 'recent_activity_map' not in locals():
                recent_activity_map = {}
                if project_ids:
                    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
                    activity_counts = self.db.query(
                        Task.project_id,
                        func.count(TaskHistory.id)
                    ).join(Task).filter(
                        Task.project_id.in_(project_ids),
                        TaskHistory.created_at >= seven_days_ago
                    ).group_by(Task.project_id).all()
                    
                    recent_activity_map = {pid: count for pid, count in activity_counts}
            
            recent_activity = recent_activity_map.get(project.id, 0)

            formatted_results.append({
                "project": project,
                "task_count": task_count,
                "completed_tasks": completed_tasks,
                "overdue_tasks": overdue_tasks,
                "member_count": member_count,
                "recent_activity": recent_activity,
                "members": members
            })
            
        logger.info(f"Retrieved {len(formatted_results)} projects with stats in {time.time() - start_time:.2f}s")
        return formatted_results
    
    def get_project_with_details(self, project_id: uuid.UUID) -> Optional[dict]:
        """Get a single project with aggregated statistics using optimized queries."""
        import time
        from sqlalchemy import case, distinct, cast, String, and_
        from models.task import TaskStatus, Task
        from models.project import ProjectMember
        from models.task_history import TaskHistory
        from datetime import datetime, timedelta, timezone

        start_time = time.time()
        
        # Base query for project stats
        stats_query = self.db.query(
            Project,
            func.count(distinct(Task.id)).label("task_count"),
            func.count(distinct(
                case(
                    (cast(Task.status, String) == TaskStatus.DONE.value, Task.id),
                    else_=None
                )
            )).label("completed_tasks"),
            func.count(distinct(
                case(
                    (and_(
                        cast(Task.status, String) != TaskStatus.DONE.value,
                        Task.due_date < datetime.now(timezone.utc)
                    ), Task.id),
                    else_=None
                )
            )).label("overdue_tasks"),
            func.count(distinct(ProjectMember.id)).label("member_count")
        ).outerjoin(
            Task, Task.project_id == Project.id
        ).outerjoin(
            ProjectMember, ProjectMember.project_id == Project.id
        ).filter(
            Project.id == project_id
        ).group_by(Project.id)
        
        result = stats_query.first()
        
        if not result:
            return None
            
        project, task_count, completed_tasks, overdue_tasks, member_count = result
        
        # Get members with user data
        members = self.db.query(ProjectMember).options(
            selectinload(ProjectMember.user)
        ).filter(ProjectMember.project_id == project_id).all()
        
        # Recent activity count
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_activity = self.db.query(func.count(TaskHistory.id)).join(Task).filter(
            Task.project_id == project_id,
            TaskHistory.created_at >= seven_days_ago
        ).scalar() or 0

        logger.debug(f"Retrieved project details in {time.time() - start_time:.2f}s")
        
        return {
            "project": project,
            "task_count": task_count,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "member_count": member_count,
            "recent_activity": recent_activity,
            "members": members
        }
    
    def create_project(self, project_data: ProjectCreate, owner_id: uuid.UUID) -> Project:
        """
        Create a new project.
        Uses explicit transaction management to ensure all related data (members)
        is created atomically.
        """
        logger.debug(f"Starting project creation with data: {project_data}, owner_id: {owner_id}")
        
        try:
            # Main transaction for project creation
            # Note: We rely on the session (self.db) to manage the transaction state
            # but we'll use savepoints (begin_nested) for critical sections if needed,
            # though here a single transaction is likely sufficient.
            
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
            logger.debug(f"Owner added as member with role: {MemberRole.OWNER.value}")
            
            # Aditonal members
            if project_data.members:
                logger.debug(f"Adding {len(project_data.members)} members to project {db_project.id}")
                
                # Batch fetch users to avoid N+1 queries
                user_ids = []
                for m in project_data.members:
                    try:
                        user_ids.append(uuid.UUID(str(m.user_id)))
                    except ValueError:
                        logger.warning(f"Invalid UUID provided in members list: {m.user_id}")
                
                if user_ids:
                    # Fetch all users in one query
                    existing_users = self.db.query(User).filter(User.id.in_(user_ids)).all()
                    existing_user_ids = {u.id for u in existing_users}
                    
                    for member_data in project_data.members:
                        try:
                            uid = uuid.UUID(str(member_data.user_id))
                            if uid not in existing_user_ids:
                                logger.warning(f"User {uid} not found, skipping addition to project")
                                continue

                            # Validate role
                            role_value = member_data.role
                            if role_value == 'admin':
                                role_value = MemberRole.ADMIN.value
                            elif role_value == 'member':
                                role_value = MemberRole.MEMBER.value
                            # If 'owner' is passed, we might want to allow allowed? usually only 1 owner.
                            # Assuming additional members are not owners.
                            
                            new_member = ProjectMember(
                                project_id=db_project.id,
                                user_id=uid,
                                role=role_value
                            )
                            self.db.add(new_member)
                        except ValueError:
                            pass
            
            # Commit the transaction - ALL OR NOTHING
            self.db.commit()
            self.db.refresh(db_project)
            logger.info(f"Project creation completed successfully")
            
            return db_project
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"IntegrityError occurred: {e}")
            raise ValueError(f"Project creation failed due to database constraint: {str(e)}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error occurred: {e}")
            raise ValueError(f"Project creation failed: {str(e)}")

    def _add_member_to_session(self, project_id: uuid.UUID, member_data: ProjectMemberCreate) -> None:
        """Helper to add member to session without committing."""
        try:
            # Check if user exists
            user_uuid = uuid.UUID(str(member_data.user_id))
            user = self.db.query(User).filter(User.id == user_uuid).first()
            if not user:
                logger.warning(f"User {member_data.user_id} not found, skipping")
                return

            # Check duplication in current session or DB
            # For new projects, DB duplication is unlikely unless concurrent,
            # but we should check if multiple members with same ID were passed in list
            # We trust the DB constraints mainly, but safe check:
            
            # Validate role
            role_value = member_data.role
            if role_value == 'admin':
                role_value = MemberRole.ADMIN.value
            elif role_value == 'member':
                role_value = MemberRole.MEMBER.value
            
            new_member = ProjectMember(
                project_id=project_id,
                user_id=user_uuid,
                role=role_value
            )
            self.db.add(new_member)
        except ValueError:
             logger.warning(f"Invalid UUID format for user_id: {member_data.user_id}, skipping")
    
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
            
        # Handle member updates
        if project_data.member_ids is not None:
            # Fetch current members
            current_members = self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
            current_user_ids = {m.user_id for m in current_members}
            new_user_ids = set(project_data.member_ids)
            
            # Determine additions and removals
            to_add_ids = new_user_ids - current_user_ids
            to_remove_ids = current_user_ids - new_user_ids
            
            # Protect owner from removal
            if project.owner_id in to_remove_ids:
                to_remove_ids.remove(project.owner_id)
                
            # Add new members
            for uid in to_add_ids:
                # Verify user exists
                user_exists = self.db.query(User.id).filter(User.id == uid).first()
                if user_exists:
                    new_member = ProjectMember(
                        project_id=project_id,
                        user_id=uid,
                        role=MemberRole.MEMBER.value
                    )
                    self.db.add(new_member)
            
            # Remove members
            if to_remove_ids:
                self.db.query(ProjectMember).filter(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id.in_(list(to_remove_ids))
                ).delete(synchronize_session=False)

            if to_add_ids or to_remove_ids:
                 changes["members"] = f"Added {len(to_add_ids)}, Removed {len(to_remove_ids)}"
        
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
        
        # Only owner OR system admin can delete project
        is_system_admin = False
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.role == 'admin':
            is_system_admin = True

        if project.owner_id != user_id and not is_system_admin:
            logger.error(f"User {user_id} is not owner or system admin of project {project_id}")
            raise ValueError("Only project owners can delete projects")
        
        try:
            # 1. Delete direct project children
            self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id).delete()
            self.db.query(TaskHistory).filter(TaskHistory.project_id == project_id).delete()
            self.db.query(ProjectAnalytics).filter(ProjectAnalytics.project_id == project_id).delete()
            self.db.query(UserProductivity).filter(UserProductivity.project_id == project_id).delete()
            self.db.query(ProjectMilestone).filter(ProjectMilestone.project_id == project_id).delete()
            self.db.query(ProjectTagAssociation).filter(ProjectTagAssociation.project_id == project_id).delete()
            
            # 2. Delete task children (Comments, Attachments, TimeTracking, Dependencies)
            subquery_tasks = self.db.query(Task.id).filter(Task.project_id == project_id)

            self.db.query(TaskComment).filter(TaskComment.task_id.in_(subquery_tasks)).delete(synchronize_session=False)
            self.db.query(TaskAttachment).filter(TaskAttachment.task_id.in_(subquery_tasks)).delete(synchronize_session=False)
            self.db.query(TaskTimeTracking).filter(TaskTimeTracking.task_id.in_(subquery_tasks)).delete(synchronize_session=False)

            # Dependencies: check both task_id and depends_on_task_id
            self.db.query(TaskDependency).filter(
                (TaskDependency.task_id.in_(subquery_tasks)) | 
                (TaskDependency.depends_on_task_id.in_(subquery_tasks))
            ).delete(synchronize_session=False)
            
            # 3. Delete tasks
            self.db.query(Task).filter(Task.project_id == project_id).delete(synchronize_session=False)
            
            # 4. Finally delete project
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
            selectinload(ProjectMember.user)
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
            logger.warning(f"add_project_member: Invalid UUID format for user_id: {member_data.user_id}")
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
                    selectinload(ProjectMember.user)
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
        logger.info(f"update_member_role service called:")
        logger.info(f"- project_id: {project_id}")
        logger.info(f"- member_user_id: {member_user_id}")
        logger.info(f"- new_role: {new_role}")
        logger.info(f"- user_id: {user_id}")
        
        project = self.get_project_by_id(project_id)
        if not project:
            logger.error(f"Project not found: {project_id}")
            raise ValueError("Project not found")
        
        logger.info(f"Found project: {project.name}, owner: {project.owner_id}")
        
        # Only owner can change roles
        if project.owner_id != user_id:
            logger.error(f"User {user_id} is not owner of project {project_id}")
            raise ValueError("Only project owners can change member roles")
        
        # Cannot change owner's role
        if project.owner_id == member_user_id:
            logger.error(f"Attempting to change owner's role: {member_user_id}")
            raise ValueError("Cannot change owner's role")
        
        member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_user_id
        ).first()
        
        if not member:
            logger.error(f"Member not found: {member_user_id} in project {project_id}")
            raise ValueError("Member not found")
        
        logger.info(f"Found member: {member.id}, current role: {member.role}")
        
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
                logger.error(f"Invalid role: {new_role}")
                raise ValueError(f"Invalid role: {new_role}")
            
            logger.info(f"Updating role from {member.role} to {role_value}")
            member.role = role_value
            self.db.commit()
            self.db.refresh(member)
            logger.info(f"Successfully updated role in database")
            
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
                selectinload(ProjectMember.user)
            ).filter(ProjectMember.id == member.id).first()
            
            logger.info(f"Returning updated member with user data")
            return member_with_user
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"IntegrityError in update_member_role: {e}")
            raise ValueError("Failed to update member role")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error in update_member_role: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise ValueError(f"Failed to update member role: {str(e)}")
    
    
    def is_project_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is a member of project."""
        # Check if user is owner
        is_owner = self.db.query(Project.id).filter(
            Project.id == project_id,
            Project.owner_id == user_id
        ).first() is not None
        
        if is_owner:
            return True

        # Check directly in ProjectMember table. 
        # This covers both regular members and owners (as owners are added as members)
        return self.db.query(ProjectMember.id).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first() is not None
    
    def is_project_admin(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is owner or admin of project."""
        # Check system admin role
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.role == 'admin':
            return True

        # Check if user is owner
        is_owner = self.db.query(Project.id).filter(
            Project.id == project_id,
            Project.owner_id == user_id
        ).first() is not None
        
        if is_owner:
            return True

        # Check directly in ProjectMember table for OWNER or ADMIN role
        return self.db.query(ProjectMember.id).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.role.in_([MemberRole.OWNER.value, MemberRole.ADMIN.value])
        ).first() is not None