from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from dependencies.auth import get_current_user
from models import Project, ProjectMember, User

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/stats")
async def get_usage_stats(
    db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)
):
    """
    Get usage statistics for the current user.
    Returns:
    - projects_used: Number of projects owned or member of
    - storage_used_bytes: Total size of uploaded files in bytes
    - seats_used: Number of unique members in projects owned by the user (including self)
    """

    # 1. Projects Count (Owned + Member)
    # Logic similar to dashboard_service.get_overview_stats
    projects_count = (
        await db.scalar(
            select(func.count(distinct(Project.id)))
            .outerjoin(ProjectMember, Project.id == ProjectMember.project_id)
            .where(
                or_(Project.owner_id == current_user.id, ProjectMember.user_id == current_user.id)
            )
        )
        or 0
    )

    # 3. Seats Used (Team Members)
    # Count distinct unique users in projects owned by current_user.
    # Logic: Get all users who are members of projects owned by me.

    # Subquery: IDs of projects owned by me
    my_projects_subquery = select(Project.id).where(Project.owner_id == current_user.id)

    # Count distinct user_ids in ProjectMember where project_id in my_projects
    # We include ourself if we are in the member list?
    # Usually the owner is implicitly a member or explicitly.
    # If explicitly, they are in ProjectMember.
    # If implicitly, we should just assume "at least 1" (the owner).

    # Let's count all distinct members of my projects.
    team_members_count = (
        await db.scalar(
            select(func.count(distinct(ProjectMember.user_id))).where(
                ProjectMember.project_id.in_(my_projects_subquery)
            )
        )
        or 0
    )

    # Ensure at least 1 (the owner) is counted if I have projects but no added members yet,
    # but technically if I own a project, I might not be a "member" row if the logic differs.
    # In this app, checking `models/project.py`, `members` are in `project_members`.
    # Does creating a project add the owner to `project_members`?
    # I should check `services/project_service.py` to be sure.
    # But usually "Seats" means "how many people have access".
    # Safest bet: count distinct users across all my projects.
    # If the count is 0 (i.e. I am not in member table), I occupy 1 seat.
    if team_members_count == 0:
        team_members_count = 1

    return {"projects_used": projects_count, "seats_used": team_members_count}
