"""
Async Project service layer for project management.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import String, and_, case, cast, delete, distinct, func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.analytics import (
    ProjectAnalytics,
    ProjectMilestone,
    ProjectTagAssociation,
    TaskAttachment,
    TaskComment,
    TaskDependency,
    TaskTimeTracking,
    UserProductivity,
)
from models.payment import Subscription
from models.project import MemberRole, Project, ProjectMember
from models.task import Task, TaskStatus
from models.task_history import TaskHistory
from models.user import User
from models.user_favorite import UserFavorite
from schemas.payment import PLAN_DETAILS, SubscriptionPlanEnum
from schemas.project import ProjectCreate, ProjectMemberCreate, ProjectUpdate
from services.async_task_history_service import AsyncTaskHistoryService
from services.cache_invalidation import (
    get_project_cache_user_ids,
    invalidate_dashboard_and_analytics_cache,
)
from utils.logger import logger


class AsyncProjectService:
    """Async Service class for project operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_user_plan_limits(self, user_id: uuid.UUID) -> dict:
        """Get plan limits for a user."""
        res = await self.db.execute(select(Subscription).filter(Subscription.user_id == user_id))
        subscription = res.scalars().first()

        plan_enum = SubscriptionPlanEnum.FREE
        if subscription:
            # Map string plan to Enum
            try:
                plan_enum = SubscriptionPlanEnum(
                    subscription.plan.value
                    if hasattr(subscription.plan, "value")
                    else subscription.plan
                )
            except ValueError:
                plan_enum = SubscriptionPlanEnum.FREE

        # Reserved for potential future use
        _ = PLAN_DETAILS.get(plan_enum)

        limits = {
            SubscriptionPlanEnum.FREE: {"projects": 2, "members": 3},
            SubscriptionPlanEnum.STARTER: {"projects": 5, "members": 5},
            SubscriptionPlanEnum.PRO: {"projects": 15, "members": 15},
            SubscriptionPlanEnum.ENTERPRISE: {"projects": float("inf"), "members": float("inf")},
        }

        return limits.get(plan_enum, limits[SubscriptionPlanEnum.FREE])  # type: ignore

    async def _check_project_limit(self, user_id: uuid.UUID) -> bool:
        """Check if user can create more projects."""
        limits = await self._get_user_plan_limits(user_id)
        max_projects = limits["projects"]

        if max_projects == float("inf"):
            return True

        res = await self.db.execute(
            select(func.count(Project.id)).filter(Project.owner_id == user_id)
        )
        current_count = res.scalar() or 0
        return bool(current_count < max_projects)

    async def _check_member_limit(self, owner_id: uuid.UUID, potential_total_count: int) -> bool:
        """
        Check if project can have this many members.
        Note: The limit is enforced based on the OWNER'S plan.
        """
        limits = await self._get_user_plan_limits(owner_id)
        max_members = limits["members"]

        if max_members == float("inf"):
            return True

        return bool(potential_total_count <= max_members)

    async def get_project_by_id(self, project_id: uuid.UUID) -> Project | None:
        """Get project by ID."""
        result = await self.db.execute(select(Project).filter(Project.id == project_id))
        return result.scalars().first()

    async def get_projects(
        self, skip: int = 0, limit: int = 100, user_id: uuid.UUID | None = None
    ) -> list[Project]:
        """Get projects with pagination, optionally filtered by user."""
        query = select(Project)
        if user_id:
            query = query.filter(
                or_(
                    Project.owner_id == user_id,
                    Project.members.any(ProjectMember.user_id == user_id),
                )
            )

        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    def _apply_project_list_filters(
        self,
        projects_query: Any,
        search: str | None,
        status_filter: str | None,
        sort_by: str,
    ) -> Any:
        """Apply server-side project list search, status filter, and stable sort."""
        if search:
            search = search.strip()[:100]
        if search:
            escaped_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            search_term = f"%{escaped_search}%"
            projects_query = projects_query.filter(
                or_(
                    Project.name.ilike(search_term, escape="\\"),
                    Project.description.ilike(search_term, escape="\\"),
                )
            )

        if status_filter == "active":
            projects_query = projects_query.filter(Project.is_active == True)
        elif status_filter in {"archived", "suspended"}:
            projects_query = projects_query.filter(Project.is_active == False)

        if sort_by == "name":
            return projects_query.order_by(Project.name.asc(), Project.id.asc())
        if sort_by == "oldest":
            return projects_query.order_by(Project.created_at.asc(), Project.id.asc())
        return projects_query.order_by(Project.created_at.desc(), Project.id.asc())

    async def get_projects_with_stats(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: uuid.UUID | None = None,
        user_projects_only: bool = False,
        search: str | None = None,
        status_filter: str | None = None,
        sort_by: str = "newest",
    ) -> list[dict]:
        """
        Get projects with aggregated statistics using bounded queries.
        Avoids Cartesian product explosion from multiple JOINs.
        """
        import time
        from collections import defaultdict

        start_time = time.time()

        # 1. Fetch Projects First (Paginated)
        projects_query = select(Project)

        if user_id:
            if user_projects_only:
                projects_query = projects_query.filter(Project.owner_id == user_id)
            else:
                # Use exists or subquery for filtering
                accessible_projects_subq = (
                    select(Project.id)
                    .outerjoin(ProjectMember, Project.id == ProjectMember.project_id)
                    .filter(or_(Project.owner_id == user_id, ProjectMember.user_id == user_id))
                )
                projects_query = projects_query.filter(Project.id.in_(accessible_projects_subq))

        projects_query = self._apply_project_list_filters(
            projects_query, search, status_filter, sort_by
        )
        projects_query = projects_query.offset(skip).limit(limit)

        result = await self.db.execute(projects_query)
        projects = list(result.scalars().all())

        if not projects:
            return []

        project_ids = [p.id for p in projects]

        # 2. Batched Fetching of Related Stats

        # B3: Combined Task Statistics + Member Count Query (merged 2 queries into 1)
        async def get_task_and_member_stats():
            stmt = (
                select(
                    Task.project_id,
                    func.count(distinct(Task.id)).label("total"),
                    func.sum(
                        case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)
                    ).label("completed"),
                    func.sum(
                        case(
                            (
                                and_(
                                    cast(Task.status, String) != TaskStatus.DONE.value,
                                    Task.due_date < datetime.now(UTC),
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("overdue"),
                )
                .filter(Task.project_id.in_(project_ids))
                .group_by(Task.project_id)
            )

            res = await self.db.execute(stmt)
            return {row.project_id: row for row in res.all()}

        async def get_member_counts():
            stmt = (
                select(ProjectMember.project_id, func.count(ProjectMember.id))
                .filter(ProjectMember.project_id.in_(project_ids))
                .group_by(ProjectMember.project_id)
            )
            res = await self.db.execute(stmt)
            return {row[0]: row[1] for row in res.all()}

        async def get_member_previews():
            ranked_members = (
                select(
                    ProjectMember.id.label("id"),
                    func.row_number()
                    .over(
                        partition_by=ProjectMember.project_id,
                        order_by=ProjectMember.joined_at.asc(),
                    )
                    .label("rank"),
                )
                .filter(ProjectMember.project_id.in_(project_ids))
                .subquery()
            )
            stmt = (
                select(ProjectMember)
                .options(selectinload(ProjectMember.user))
                .join(ranked_members, ProjectMember.id == ranked_members.c.id)
                .filter(ranked_members.c.rank <= 5)
            )
            res = await self.db.execute(stmt)
            m_map: defaultdict[uuid.UUID, list[ProjectMember]] = defaultdict(list)
            for m in res.scalars().all():
                m_map[m.project_id].append(m)
            return m_map

        # Activity Query (Batched)
        async def get_activity():
            seven_days_ago = datetime.now(UTC) - timedelta(days=7)
            stmt = (
                select(TaskHistory.project_id, func.count(TaskHistory.id))
                .filter(
                    TaskHistory.project_id.in_(project_ids),
                    TaskHistory.created_at >= seven_days_ago,
                )
                .group_by(TaskHistory.project_id)
            )

            res = await self.db.execute(stmt)
            return {row[0]: row[1] for row in res.all()}

        task_stats_map = await get_task_and_member_stats()
        member_count_map = await get_member_counts()
        members_map = await get_member_previews()
        activity_map = await get_activity()

        # 3. Assemble Results
        formatted_results = []
        for project in projects:
            stats = task_stats_map.get(project.id)
            members = members_map.get(project.id, [])
            member_count = member_count_map.get(project.id, 0)
            activity = activity_map.get(project.id, 0)

            # Extract stats safely
            task_count = stats.total if stats else 0
            # Check for None explicitly as sum can return None
            completed = stats.completed if stats and stats.completed is not None else 0
            overdue = stats.overdue if stats and stats.overdue is not None else 0

            formatted_results.append(
                {
                    "project": project,
                    "task_count": task_count,
                    "completed_tasks": completed,
                    "overdue_tasks": overdue,
                    "member_count": member_count,
                    "recent_activity": activity,
                    "members": members,
                }
            )

        logger.info(f"Async projects fetch optimized took {time.time() - start_time:.2f}s")
        return formatted_results

    async def create_project(self, project_data: ProjectCreate, owner_id: uuid.UUID) -> Project:  # noqa: PLR0912
        """Create a new project."""
        try:
            db_project = Project(
                name=project_data.name,
                description=project_data.description,
                color=project_data.color,
                settings=project_data.settings,
                owner_id=owner_id,
            )

            # Check project limits before creation
            if not await self._check_project_limit(owner_id):
                raise ValueError(
                    "Project limit reached for current subscription plan. Please upgrade to create more projects."
                )

            self.db.add(db_project)
            await self.db.flush()

            # Add owner as member
            owner_member = ProjectMember(
                project_id=db_project.id, user_id=owner_id, role=MemberRole.OWNER.value
            )
            self.db.add(owner_member)
            cache_user_ids = {owner_id}

            # Additional members
            if project_data.members:
                requested_members: dict[uuid.UUID, str] = {}
                for member_data in project_data.members:
                    try:
                        member_id = uuid.UUID(str(member_data.user_id))
                    except ValueError as exc:
                        raise ValueError("Invalid project member ID") from exc
                    if member_id == owner_id:
                        continue
                    requested_members.setdefault(member_id, member_data.role)

                # Check member limits (owner plus unique requested members).
                current_count = 1
                new_count = len(requested_members)
                if not await self._check_member_limit(owner_id, current_count + new_count):
                    raise ValueError(
                        "Team member limit reached. Your plan allows fewer members per project."
                    )

                if requested_members:
                    res = await self.db.execute(
                        select(User.id).filter(User.id.in_(requested_members))
                    )
                    existing_ids = set(res.scalars().all())
                    missing_ids = set(requested_members) - existing_ids
                    if missing_ids:
                        raise ValueError("One or more project members were not found")

                    for uid, role_value in requested_members.items():
                        if role_value not in {
                            MemberRole.ADMIN.value,
                            MemberRole.MEMBER.value,
                        }:
                            role_value = MemberRole.MEMBER.value
                        self.db.add(
                            ProjectMember(project_id=db_project.id, user_id=uid, role=role_value)
                        )
                        cache_user_ids.add(uid)

            await self.db.commit()
            await self.db.refresh(db_project)
            await invalidate_dashboard_and_analytics_cache(user_ids=cache_user_ids)
            return db_project

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating project: {e}")
            raise ValueError(
                "Project with this name might already exist or violates other constraints."
            )
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating project: {e}")
            raise ValueError("Database error occurred while creating project.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error creating project: {e}")
            raise ValueError(f"Project creation failed: {e!s}")

    async def _sync_project_members(
        self,
        project_id: uuid.UUID,
        owner_id: uuid.UUID,
        requested_member_ids: list[uuid.UUID],
    ) -> tuple[set[uuid.UUID], set[uuid.UUID]]:
        """Make project membership match requested user IDs and preserve owner access."""
        requested_ids = set(requested_member_ids)
        requested_ids.discard(owner_id)

        if not await self._check_member_limit(owner_id, len(requested_ids) + 1):
            raise ValueError(
                "Team member limit reached. Your plan allows fewer members per project."
            )

        if requested_ids:
            users_result = await self.db.execute(select(User.id).where(User.id.in_(requested_ids)))
            valid_ids = set(users_result.scalars().all())
            if missing_ids := requested_ids - valid_ids:
                raise ValueError(f"One or more project members were not found: {missing_ids}")

        existing_result = await self.db.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id)
        )
        existing_members = list(existing_result.scalars().all())
        existing_by_user = {member.user_id: member for member in existing_members}
        existing_ids = set(existing_by_user)
        desired_ids = requested_ids | {owner_id}
        removed_ids = (existing_ids - desired_ids) - {owner_id}

        if removed_ids:
            await self.db.execute(
                update(Task)
                .where(Task.project_id == project_id, Task.assignee_id.in_(removed_ids))
                .values(assignee_id=None)
            )
            await self.db.execute(
                delete(ProjectMember).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id.in_(removed_ids),
                )
            )

        owner_member = existing_by_user.get(owner_id)
        if owner_member is None:
            self.db.add(
                ProjectMember(project_id=project_id, user_id=owner_id, role=MemberRole.OWNER.value)
            )
        elif owner_member.role != MemberRole.OWNER.value:
            owner_member.role = MemberRole.OWNER.value

        for member_id in sorted(requested_ids - existing_ids, key=str):
            self.db.add(
                ProjectMember(
                    project_id=project_id,
                    user_id=member_id,
                    role=MemberRole.MEMBER.value,
                )
            )

        return desired_ids, existing_ids | desired_ids

    async def update_project(
        self, project_id: uuid.UUID, project_data: ProjectUpdate, user_id: uuid.UUID
    ) -> Project:
        """Update project information."""
        project = await self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        if not await self.is_project_admin(project_id, user_id):
            raise ValueError("Only project owners and admins can update projects")

        changes: dict[str, Any] = {}
        if project_data.name is not None:
            changes["name"] = project_data.name
            project.name = project_data.name
        if project_data.description is not None:
            changes["description"] = project_data.description
            project.description = project_data.description
        if project_data.color is not None and project_data.color != project.color:
            changes["color"] = project_data.color
            project.color = project_data.color
        if project_data.settings is not None and project_data.settings != project.settings:
            changes["settings"] = project_data.settings
            project.settings = project_data.settings
        if project_data.is_active is not None:
            changes["is_active"] = project_data.is_active
            project.is_active = project_data.is_active

        cache_member_ids: set[uuid.UUID] = set()
        if project_data.member_ids is not None:
            desired_ids, cache_member_ids = await self._sync_project_members(
                project_id, project.owner_id, project_data.member_ids
            )
            changes["member_ids"] = [str(member_id) for member_id in sorted(desired_ids, key=str)]

        try:
            cache_user_ids = await get_project_cache_user_ids(
                self.db,
                project_id,
                (user_id, *cache_member_ids),
            )
            if changes:
                history_service = AsyncTaskHistoryService(self.db)
                await history_service.log_project_updated(
                    project_id, user_id, changes, commit=False
                )
            await self.db.commit()
            await self.db.refresh(project)
            await invalidate_dashboard_and_analytics_cache(user_ids=cache_user_ids)

            return project
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error updating project {project_id}: {e}")
            raise ValueError("Database error occurred while updating project.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error updating project {project_id}: {e}")
            raise ValueError("Project update failed")

    async def delete_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a project."""
        project = await self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        # Check permission
        res = await self.db.execute(select(User).filter(User.id == user_id))
        user = res.scalars().first()
        is_system_admin = user.role == "admin" if user else False

        if project.owner_id != user_id and not is_system_admin:
            raise ValueError("Only project owners can delete projects")

        try:
            cache_user_ids = await get_project_cache_user_ids(self.db, project_id, (user_id,))

            task_ids = select(Task.id).where(Task.project_id == project_id)

            # Delete dependent rows explicitly. Existing deployments do not
            # consistently define database-level cascades for this graph.
            await self.db.execute(delete(TaskHistory).where(TaskHistory.project_id == project_id))
            await self.db.execute(
                delete(TaskDependency).where(
                    TaskDependency.task_id.in_(task_ids)
                    | TaskDependency.depends_on_task_id.in_(task_ids)
                )
            )
            await self.db.execute(delete(TaskComment).where(TaskComment.task_id.in_(task_ids)))
            await self.db.execute(
                delete(TaskAttachment).where(TaskAttachment.task_id.in_(task_ids))
            )
            await self.db.execute(
                delete(TaskTimeTracking).where(TaskTimeTracking.task_id.in_(task_ids))
            )
            await self.db.execute(
                delete(ProjectAnalytics).where(ProjectAnalytics.project_id == project_id)
            )
            await self.db.execute(
                delete(UserProductivity).where(UserProductivity.project_id == project_id)
            )
            await self.db.execute(
                delete(ProjectMilestone).where(ProjectMilestone.project_id == project_id)
            )
            await self.db.execute(
                delete(ProjectTagAssociation).where(ProjectTagAssociation.project_id == project_id)
            )
            await self.db.execute(delete(UserFavorite).where(UserFavorite.project_id == project_id))
            await self.db.execute(
                delete(ProjectMember).where(ProjectMember.project_id == project_id)
            )
            await self.db.execute(delete(Task).where(Task.project_id == project_id))
            await self.db.execute(delete(Project).where(Project.id == project_id))

            await self.db.commit()
            await invalidate_dashboard_and_analytics_cache(user_ids=cache_user_ids)
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error deleting project {project_id}: {e}")
            raise ValueError("Database error occurred while deleting project.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error deleting project {project_id}: {e}")
            raise ValueError(f"Delete failed: {e}")

    async def is_project_admin(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is owner or admin of project."""
        # Check system admin
        res = await self.db.execute(select(User).filter(User.id == user_id))
        user = res.scalars().first()
        if user and user.role == "admin":
            return True

        # Check owner
        res_owner = await self.db.execute(
            select(Project).filter(Project.id == project_id, Project.owner_id == user_id)
        )
        if res_owner.scalars().first():
            return True

        # Check member role
        res_member = await self.db.execute(
            select(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
                ProjectMember.role.in_([MemberRole.OWNER.value, MemberRole.ADMIN.value]),
            )
        )
        return res_member.scalars().first() is not None

    async def is_project_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is a member of project."""
        # Check owner
        res_owner = await self.db.execute(
            select(Project).filter(Project.id == project_id, Project.owner_id == user_id)
        )
        if res_owner.scalars().first():
            return True

        # Check member
        res_member = await self.db.execute(
            select(ProjectMember).filter(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
            )
        )
        return res_member.scalars().first() is not None

    async def get_project_members(
        self,
        project_id: uuid.UUID,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[ProjectMember]:
        """Get project members, optionally bounded for API list responses."""
        query = (
            select(ProjectMember)
            .options(selectinload(ProjectMember.user))
            .filter(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at.asc())
        )
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def add_project_member(  # noqa: PLR0912
        self,
        project_id: uuid.UUID,
        member_data: ProjectMemberCreate,
        user_id: uuid.UUID,
        *,
        commit: bool = True,
    ) -> ProjectMember:
        """Add a member to a project."""
        project = await self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        if not await self.is_project_admin(project_id, user_id):
            raise ValueError("Only project owners and admins can add members")

        try:
            user_uuid = uuid.UUID(str(member_data.user_id))
            # Check existing
            res = await self.db.execute(
                select(ProjectMember).filter(
                    ProjectMember.project_id == project_id, ProjectMember.user_id == user_uuid
                )
            )
            if res.scalars().first():
                raise ValueError("User is already a project member")

            # Check member limits
            current_member_res = await self.db.execute(
                select(func.count(ProjectMember.id)).filter(ProjectMember.project_id == project_id)
            )
            current_member_count = current_member_res.scalar() or 0

            if not await self._check_member_limit(project.owner_id, current_member_count + 1):
                raise ValueError(
                    "Team member limit reached for this project (based on owner's plan)."
                )

            # Create member
            role_value = member_data.role
            if role_value == "admin":
                role_value = MemberRole.ADMIN.value
            elif role_value == "member":
                role_value = MemberRole.MEMBER.value
            elif role_value == "owner":
                role_value = MemberRole.OWNER.value

            db_member = ProjectMember(project_id=project_id, user_id=user_uuid, role=role_value)
            self.db.add(db_member)
            cache_user_ids = await get_project_cache_user_ids(
                self.db, project_id, (user_id, user_uuid)
            )
            await self.db.flush()
            if commit:
                await self.db.commit()
            await self.db.refresh(db_member)
            await invalidate_dashboard_and_analytics_cache(user_ids=cache_user_ids)

            # Log activity
            try:
                history_service = AsyncTaskHistoryService(self.db)
                added_user_res = await self.db.execute(select(User).filter(User.id == user_uuid))
                added_user = added_user_res.scalars().first()
                if added_user:
                    await history_service.log_project_member_added(
                        project_id,
                        added_user.name or "Unknown User",
                        user_id,
                        commit=commit,
                    )
            except Exception as e:
                logger.error(f"Failed to log activity: {e}")

            # Load with user
            res_loaded = await self.db.execute(
                select(ProjectMember)
                .options(selectinload(ProjectMember.user))
                .filter(ProjectMember.id == db_member.id)
            )
            member = res_loaded.scalars().first()
            if not member:
                raise ValueError("Failed to retrieve created member")
            return member

        except ValueError as e:
            raise e
        except Exception as e:
            await self.db.rollback()
            raise ValueError(f"Failed to add project member: {e}")

    async def remove_project_member(
        self,
        project_id: uuid.UUID,
        member_user_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        commit: bool = True,
    ) -> bool:
        """Remove a member from a project."""
        project = await self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        if not await self.is_project_admin(project_id, user_id):
            raise ValueError("Only project owners and admins can remove members")

        if project.owner_id == member_user_id:
            raise ValueError("Cannot remove project owner")

        res = await self.db.execute(
            select(ProjectMember).filter(
                ProjectMember.project_id == project_id, ProjectMember.user_id == member_user_id
            )
        )
        member = res.scalars().first()
        if not member:
            raise ValueError("Member not found")

        try:
            # Get user name for log
            user_res = await self.db.execute(select(User).filter(User.id == member_user_id))
            user = user_res.scalars().first()
            member_name = user.name if user else "Unknown User"

            cache_user_ids = await get_project_cache_user_ids(
                self.db, project_id, (user_id, member_user_id)
            )
            # Keep task assignments linked to active project members only.
            await self.db.execute(
                update(Task)
                .where(Task.project_id == project_id, Task.assignee_id == member_user_id)
                .values(assignee_id=None)
            )
            await self.db.delete(member)
            await self.db.flush()
            if commit:
                await self.db.commit()
            await invalidate_dashboard_and_analytics_cache(user_ids=cache_user_ids)

            # Log
            try:
                history_service = AsyncTaskHistoryService(self.db)
                await history_service.log_project_member_removed(
                    project_id,
                    member_name or "Unknown User",
                    user_id,
                    commit=commit,
                )
            except Exception as e:
                logger.error(f"Failed to log activity: {e}")

            return True
        except Exception:
            await self.db.rollback()
            raise ValueError("Failed to remove project member")

    async def update_member_role(
        self, project_id: uuid.UUID, member_user_id: uuid.UUID, new_role: str, user_id: uuid.UUID
    ) -> ProjectMember:
        """Update a member's role."""
        project = await self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        if project.owner_id != user_id:
            raise ValueError("Only project owners can change member roles")

        if project.owner_id == member_user_id:
            raise ValueError("Cannot change owner's role")

        res = await self.db.execute(
            select(ProjectMember).filter(
                ProjectMember.project_id == project_id, ProjectMember.user_id == member_user_id
            )
        )
        member = res.scalars().first()
        if not member:
            raise ValueError("Member not found")

        try:
            # Log preparation
            user_res = await self.db.execute(select(User).filter(User.id == member_user_id))
            user = user_res.scalars().first()
            member_name = user.name if user else "Unknown User"

            role_value = new_role
            if role_value == "admin":
                role_value = MemberRole.ADMIN.value
            elif role_value == "member":
                role_value = MemberRole.MEMBER.value
            elif role_value == "owner":
                role_value = MemberRole.OWNER.value

            member.role = role_value
            cache_user_ids = await get_project_cache_user_ids(
                self.db, project_id, (user_id, member_user_id)
            )
            await self.db.commit()
            await self.db.refresh(member)
            await invalidate_dashboard_and_analytics_cache(user_ids=cache_user_ids)

            try:
                history_service = AsyncTaskHistoryService(self.db)
                await history_service.log_project_member_role_changed(
                    project_id, member_name or "Unknown User", new_role, user_id
                )
            except Exception as e:
                logger.error(f"Failed to log activity: {e}")

            # Load with user
            res_loaded = await self.db.execute(
                select(ProjectMember)
                .options(selectinload(ProjectMember.user))
                .filter(ProjectMember.id == member.id)
            )
            updated_member = res_loaded.scalars().first()
            if not updated_member:
                raise ValueError("Failed to retrieve updated member")
            return updated_member
        except Exception as e:
            await self.db.rollback()
            raise ValueError(f"Failed to update member role: {e}")

    async def get_project_with_details(self, project_id: uuid.UUID) -> dict | None:
        """
        Get project with details using optimized single query.
        Combines all statistics into one database round-trip to avoid N+1 problem.
        """
        # Single optimized query for project and all stats
        seven_days_ago = datetime.now(UTC) - timedelta(days=7)

        stats_query = (
            select(
                Project,
                func.count(distinct(Task.id)).label("task_count"),
                func.count(
                    distinct(
                        case(
                            (cast(Task.status, String) == TaskStatus.DONE.value, Task.id),
                            else_=None,
                        )
                    )
                ).label("completed_tasks"),
                func.count(
                    distinct(
                        case(
                            (
                                and_(
                                    cast(Task.status, String) != TaskStatus.DONE.value,
                                    Task.due_date < datetime.now(UTC),
                                ),
                                Task.id,
                            ),
                            else_=None,
                        )
                    )
                ).label("overdue_tasks"),
                func.count(distinct(ProjectMember.id)).label("member_count"),
            )
            .outerjoin(Task, Task.project_id == Project.id)
            .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
            .filter(Project.id == project_id)
            .group_by(Project.id)
        )

        result = await self.db.execute(stats_query)
        row = result.first()

        if not row:
            return None

        project = row[0]
        task_count = row[1] or 0
        completed_tasks = row[2] or 0
        overdue_tasks = row[3] or 0
        member_count = row[4] or 0

        # Separate query for recent activity (using join with TaskHistory)
        recent_activity = (
            await self.db.execute(
                select(func.count(TaskHistory.id)).filter(
                    TaskHistory.project_id == project_id,
                    TaskHistory.created_at >= seven_days_ago,
                )
            )
        ).scalar() or 0

        # Fetch members with eager loading
        members = await self.get_project_members(project_id)

        return {
            "project": project,
            "task_count": task_count,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "member_count": member_count,
            "recent_activity": recent_activity,
            "members": members,
        }

    async def add_project_members_bulk(  # noqa: PLR0912, PLR0915
        self, project_id: uuid.UUID, members_data: list[ProjectMemberCreate], user_id: uuid.UUID
    ) -> list[ProjectMember]:
        """
        Add multiple members to a project in a single transaction.
        More efficient than calling add_project_member multiple times.

        Args:
            project_id: UUID of the project
            members_data: List of ProjectMemberCreate objects
            user_id: UUID of the user performing the action

        Returns:
            List of created ProjectMember objects
        """
        project = await self.get_project_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        if not await self.is_project_admin(project_id, user_id):
            raise ValueError("Only project owners and admins can add members")

        if not members_data:
            return []

        # Check member limits
        current_member_res = await self.db.execute(
            select(func.count(ProjectMember.id)).filter(ProjectMember.project_id == project_id)
        )
        current_member_count = current_member_res.scalar() or 0

        # We need to filter out duplicates and existing members to know exact count to add
        # But this is complex in bulk. For now, assume all unique and new for limit check,
        # or just check Upper Bound (Current + Requested). Safe to overestimate.
        if not await self._check_member_limit(
            project.owner_id, current_member_count + len(members_data)
        ):
            # This might fail even if some overlap, but safer.
            raise ValueError(f"Team member limit reached. Cannot add {len(members_data)} members.")

        try:
            # Collect all user IDs to add
            user_ids_to_add = []
            for member_data in members_data:
                try:
                    user_ids_to_add.append(uuid.UUID(str(member_data.user_id)))
                except ValueError:
                    continue

            if not user_ids_to_add:
                return []

            # Check which users already exist in the project
            existing_members_result = await self.db.execute(
                select(ProjectMember.user_id).filter(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id.in_(user_ids_to_add),
                )
            )
            existing_member_ids = set(existing_members_result.scalars().all())

            # Check which users actually exist in the system
            valid_users_result = await self.db.execute(
                select(User.id, User.name).filter(User.id.in_(user_ids_to_add))
            )
            valid_users = {row[0]: row[1] for row in valid_users_result.all()}

            # Create new members
            new_members = []
            added_user_names = []

            for member_data in members_data:
                try:
                    uid = uuid.UUID(str(member_data.user_id))
                except ValueError:
                    continue

                # Skip if already a member or user doesn't exist
                if uid in existing_member_ids or uid not in valid_users:
                    continue

                # Normalize role
                role_value = member_data.role
                if role_value == "admin":
                    role_value = MemberRole.ADMIN.value
                elif role_value == "member":
                    role_value = MemberRole.MEMBER.value
                elif role_value == "owner":
                    role_value = MemberRole.OWNER.value

                db_member = ProjectMember(project_id=project_id, user_id=uid, role=role_value)
                self.db.add(db_member)
                new_members.append(db_member)
                added_user_names.append(valid_users[uid])

            if not new_members:
                return []

            cache_user_ids = await get_project_cache_user_ids(
                self.db,
                project_id,
                (user_id, *(member.user_id for member in new_members)),
            )
            await self.db.commit()
            await invalidate_dashboard_and_analytics_cache(user_ids=cache_user_ids)

            # Refresh all new members
            for member in new_members:
                await self.db.refresh(member)

            # Log activity for bulk add
            try:
                history_service = AsyncTaskHistoryService(self.db)
                if len(added_user_names) == 1:
                    await history_service.log_project_member_added(
                        project_id, added_user_names[0], user_id
                    )
                else:
                    # Log as a single activity for multiple members
                    names_str = ", ".join(added_user_names[:3])
                    if len(added_user_names) > 3:
                        names_str += f" and {len(added_user_names) - 3} others"
                    await history_service.log_project_member_added(project_id, names_str, user_id)
            except Exception as e:
                logger.error(f"Failed to log bulk add activity: {e}")

            # Load members with user data
            member_ids = [m.id for m in new_members]
            loaded_members_result = await self.db.execute(
                select(ProjectMember)
                .options(selectinload(ProjectMember.user))
                .filter(ProjectMember.id.in_(member_ids))
            )

            return list(loaded_members_result.scalars().all())

        except ValueError as e:
            raise e
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Bulk add members failed: {e}")
            raise ValueError(f"Failed to add project members: {e}")

    async def get_project_stats_summary(self, project_id: uuid.UUID) -> dict[str, Any]:
        """
        Get a lightweight stats summary for a project.
        Useful for quick dashboard displays.
        """
        stats_query = (
            select(
                func.count(distinct(Task.id)).label("task_count"),
                func.count(
                    distinct(
                        case(
                            (cast(Task.status, String) == TaskStatus.DONE.value, Task.id),
                            else_=None,
                        )
                    )
                ).label("completed_tasks"),
                func.count(distinct(ProjectMember.id)).label("member_count"),
            )
            .select_from(Project)
            .outerjoin(Task, Task.project_id == Project.id)
            .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
            .filter(Project.id == project_id)
        )

        result = await self.db.execute(stats_query)
        row = result.first()

        if not row:
            return {"task_count": 0, "completed_tasks": 0, "member_count": 0, "completion_rate": 0}

        task_count = row[0] or 0
        completed_tasks = row[1] or 0
        member_count = row[2] or 0
        completion_rate = round(completed_tasks / task_count * 100) if task_count > 0 else 0

        return {
            "task_count": task_count,
            "completed_tasks": completed_tasks,
            "member_count": member_count,
            "completion_rate": completion_rate,
        }
