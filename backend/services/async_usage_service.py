"""
Async Usage service layer for usage statistics.
Separates usage metrics logic from the router.
"""

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project, ProjectMember
from models.user import User


class AsyncUsageService:
    """Async Service class for usage statistics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_usage_stats(self, user: User) -> dict[str, int]:
        """
        Get usage statistics for a user.

        Returns:
            dict containing:
            - projects_used: Number of projects owned or member of
            - seats_used: Number of unique members in projects owned by the user (including self)
            - storage_used_bytes: Total file storage used (placeholder for now)
        """
        # 1. Projects Count (Owned + Member)
        projects_count = (
            await self.db.scalar(
                select(func.count(distinct(Project.id)))
                .outerjoin(ProjectMember, Project.id == ProjectMember.project_id)
                .where(
                    or_(Project.owner_id == user.id, ProjectMember.user_id == user.id)
                )
            )
            or 0
        )

        # 2. Seats Used (Team Members)
        # Count distinct unique users in projects owned by current_user.

        # Subquery: IDs of projects owned by me
        my_projects_subquery = select(Project.id).where(Project.owner_id == user.id)

        # Count distinct user_ids in ProjectMember where project_id in my_projects
        team_members_count = (
            await self.db.scalar(
                select(func.count(distinct(ProjectMember.user_id))).where(
                    ProjectMember.project_id.in_(my_projects_subquery)
                )
            )
            or 0
        )

        # Ensure at least 1 (the owner) is counted if I have projects but no added members yet
        # Logic: If I own a project, I occupy a seat even if I haven't added anyone else.
        # However, if I have 0 projects, I have 0 seats used? Or 1 (myself)?
        # Let's keep the logic consistent with the original: if count is 0, default to 1 (assuming user exists)
        if team_members_count == 0:
            team_members_count = 1

        return {
            "projects_used": projects_count,
            "seats_used": team_members_count,
            "storage_used_bytes": 0  # Placeholder for future file storage logic
        }
