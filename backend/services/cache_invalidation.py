"""Shared cache invalidation operations used after data mutations."""

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project, ProjectMember
from utils.logger import setup_logger

logger = setup_logger("cache_invalidation")


async def invalidate_auth_user_cache(user_id: uuid.UUID | str) -> None:
    """Invalidate the short-lived authenticated-user snapshot."""
    try:
        from services.auth_cache import invalidate_auth_user_cache as _invalidate

        await _invalidate(user_id)
    except Exception as exc:
        logger.warning(f"Failed to invalidate auth cache: {exc}")


async def invalidate_dashboard_and_analytics_cache(
    user_id: uuid.UUID | None = None,
    *,
    user_ids: Iterable[uuid.UUID] | None = None,
) -> None:
    """Invalidate only the affected users, or all users for global changes."""
    try:
        from services.async_analytics_service import invalidate_analytics_cache
        from services.async_dashboard_service import invalidate_dashboard_cache

        affected_ids = {affected_id for affected_id in (user_ids or ()) if affected_id is not None}
        if user_id is not None:
            affected_ids.add(user_id)

        if not affected_ids:
            await invalidate_dashboard_cache()
            await invalidate_analytics_cache()
            return

        for affected_id in affected_ids:
            await invalidate_dashboard_cache(affected_id)
            await invalidate_analytics_cache(affected_id)
    except Exception as exc:
        logger.exception(f"Failed to invalidate dashboard/analytics cache: {exc}")


async def get_project_cache_user_ids(
    db: AsyncSession,
    project_id: uuid.UUID,
    extra_user_ids: Iterable[uuid.UUID] = (),
) -> set[uuid.UUID]:
    """Collect project participants whose dashboard data can change."""
    user_ids = {user_id for user_id in extra_user_ids if user_id is not None}
    try:
        result = await db.execute(select(Project.owner_id).where(Project.id == project_id))
        owner_id = result.scalar_one_or_none()

        member_result = await db.execute(
            select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)
        )
        user_ids.update(member_result.scalars().all())
        if owner_id is not None:
            user_ids.add(owner_id)
    except Exception as exc:
        logger.warning(f"Failed to collect project cache users: {exc}")
    return user_ids
