"""
User Favorites router for managing user's favorite projects.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from models import Project, User, UserFavorite
from routers.auth import get_current_active_user
from utils.logger import setup_logger
from utils.schema_utils import to_camel

logger = setup_logger("favorites_router")

router = APIRouter(prefix="/favorites", tags=["favorites"])

# Route-level rate limiting for favorites operations
from rate_limiter import RateLimits, limiter


class FavoriteIdsResponse(BaseModel):
    """Schema for listing favorite project IDs."""

    project_ids: list[str]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ToggleFavoriteRequest(BaseModel):
    """Schema for toggling favorite status."""

    project_id: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ToggleFavoriteResponse(BaseModel):
    """Schema for toggle favorite response."""

    is_favorite: bool
    project_id: str
    message: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


@router.get("", response_model=FavoriteIdsResponse)
@limiter.limit(RateLimits.API_READ)
async def get_favorite_project_ids(
    request: Request,
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_async_db)
):
    """
    Get list of user's favorite project IDs.
    Returns just the IDs for efficient frontend state management.
    """
    try:
        result = await db.execute(
            select(UserFavorite.project_id).where(UserFavorite.user_id == current_user.id)
        )
        project_ids = [str(row[0]) for row in result.fetchall()]

        return FavoriteIdsResponse(project_ids=project_ids)
    except Exception as e:
        logger.error(f"Error fetching favorites: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch favorites"
        )


@router.post("/toggle", response_model=ToggleFavoriteResponse)
@limiter.limit(RateLimits.FAVORITES_WRITE)
async def toggle_favorite(
    request: Request,
    toggle_request: ToggleFavoriteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Toggle favorite status for a project.
    If project is already favorited, removes it. Otherwise, adds it.
    """
    try:
        project_uuid = uuid.UUID(toggle_request.project_id)

        # Verify project exists
        project_result = await db.execute(select(Project).where(Project.id == project_uuid))
        project = project_result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        # Check if already favorited
        existing_result = await db.execute(
            select(UserFavorite).where(
                UserFavorite.user_id == current_user.id, UserFavorite.project_id == project_uuid
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            # Remove from favorites
            await db.delete(existing)
            await db.commit()

            logger.info(f"User {current_user.id} removed project {project_uuid} from favorites")

            return ToggleFavoriteResponse(
                is_favorite=False,
                project_id=toggle_request.project_id,
                message=f'"{project.name}" has been removed from your favorites.',
            )
        else:
            # Add to favorites
            new_favorite = UserFavorite(user_id=current_user.id, project_id=project_uuid)
            db.add(new_favorite)
            await db.commit()

            logger.info(f"User {current_user.id} added project {project_uuid} to favorites")

            return ToggleFavoriteResponse(
                is_favorite=True,
                project_id=toggle_request.project_id,
                message=f'"{project.name}" has been added to your favorites.',
            )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling favorite: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to toggle favorite"
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RateLimits.FAVORITES_WRITE)
async def remove_favorite(
    request: Request,
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Remove a project from favorites.
    """
    try:
        project_uuid = uuid.UUID(project_id)

        result = await db.execute(
            delete(UserFavorite).where(
                UserFavorite.user_id == current_user.id, UserFavorite.project_id == project_uuid
            )
        )
        await db.commit()

        if result.rowcount == 0:  # type: ignore
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")

        logger.info(f"User {current_user.id} removed project {project_uuid} from favorites")

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing favorite: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to remove favorite"
        )


@router.post(
    "/{project_id}", status_code=status.HTTP_201_CREATED, response_model=ToggleFavoriteResponse
)
@limiter.limit(RateLimits.FAVORITES_WRITE)
async def add_favorite(
    request: Request,
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Add a project to favorites.
    """
    try:
        project_uuid = uuid.UUID(project_id)

        # Verify project exists
        project_result = await db.execute(select(Project).where(Project.id == project_uuid))
        project = project_result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        # Check if already favorited
        existing_result = await db.execute(
            select(UserFavorite).where(
                UserFavorite.user_id == current_user.id, UserFavorite.project_id == project_uuid
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            return ToggleFavoriteResponse(
                is_favorite=True,
                project_id=project_id,
                message=f'"{project.name}" is already in your favorites.',
            )

        # Add to favorites
        new_favorite = UserFavorite(user_id=current_user.id, project_id=project_uuid)
        db.add(new_favorite)
        await db.commit()

        logger.info(f"User {current_user.id} added project {project_uuid} to favorites")

        return ToggleFavoriteResponse(
            is_favorite=True,
            project_id=project_id,
            message=f'"{project.name}" has been added to your favorites.',
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding favorite: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add favorite"
        )
