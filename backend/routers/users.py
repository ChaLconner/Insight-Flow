"""
User management router for CRUD operations.
Refactored for Async operations with proper Dependency Injection.
"""

import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from dependencies.services import get_user_service
from models.user import User
from routers.auth import get_current_active_user
from schemas.user import (
    UserInvite,
    UserResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
    UserUpdate,
)
from services.async_user_service import AsyncUserService
from utils.cloudinary_upload import init_cloudinary, is_cloudinary_configured
from utils.cloudinary_upload import upload_avatar as cloudinary_upload_avatar

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["user management"])

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize Cloudinary on module load
if is_cloudinary_configured():
    init_cloudinary()
    logger.info("Cloudinary initialized for avatar uploads")
else:
    logger.warning("Cloudinary not configured, falling back to local storage")


@router.get("/", response_model=list[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    user_service: AsyncUserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get all users."""
    return await user_service.get_users(skip=skip, limit=limit)


@router.get("/stats")
async def get_user_stats(
    user_service: AsyncUserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get user statistics."""
    return await user_service.get_user_stats()


@router.post("/invite", response_model=UserResponse)
async def invite_user(
    user_invite: UserInvite,
    user_service: AsyncUserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Invite a new user.
    Only admins and managers can invite users.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to invite users"
        )

    try:
        user = await user_service.invite_user(user_invite)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: AsyncUserService = Depends(get_user_service),
) -> Any:
    """Update current user profile."""
    try:
        updated_user = await user_service.update_user(current_user.id, user_data)
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        )


@router.get("/search/{email}", response_model=UserResponse)
async def search_user_by_email(
    email: str,
    user_service: AsyncUserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Search user by email."""
    user = await user_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/search", response_model=list[UserResponse])
async def search_users(
    q: str = "",
    skip: int = 0,
    limit: int = 20,
    role: str | None = None,
    status: str | None = None,
    user_service: AsyncUserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
) -> list[UserResponse]:
    """Search users by email or name with filters."""
    is_active = None
    if status == "active":
        is_active = True
    elif status == "inactive":
        is_active = False

    users = await user_service.search_users(
        q, skip=skip, limit=limit, role=role, is_active=is_active
    )
    return users  # type: ignore[return-value]


@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_current_user_settings(
    current_user: User = Depends(get_current_active_user),
    user_service: AsyncUserService = Depends(get_user_service),
) -> Any:
    """Get current user settings."""
    return await user_service.get_or_create_settings(current_user.id)


@router.patch("/me/settings", response_model=UserSettingsResponse)
async def update_current_user_settings(
    settings_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: AsyncUserService = Depends(get_user_service),
) -> Any:
    """Update current user settings."""
    try:
        return await user_service.update_settings(current_user.id, settings_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/me/avatar", response_model=UserResponse)
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    user_service: AsyncUserService = Depends(get_user_service),
) -> UserResponse:
    """
    Upload and update user avatar.
    Uses Cloudinary for cloud storage if configured, otherwise falls back to local storage.
    """
    try:
        file_content = await file.read()
        avatar_url = None
        old_avatar_url = current_user.avatar_url

        # Try Cloudinary upload first
        if is_cloudinary_configured():
            logger.info(f"Uploading avatar to Cloudinary for user {current_user.id}")

            filename = file.filename or "avatar.png"
            result = cloudinary_upload_avatar(
                file_content=file_content, filename=filename, user_id=str(current_user.id)
            )

            if result and result.get("secure_url"):
                avatar_url = result["secure_url"]
                logger.info(f"Avatar uploaded to Cloudinary: {avatar_url}")

                # Delete old local avatar if user is switching from local to Cloudinary
                if old_avatar_url and old_avatar_url.startswith("/static/uploads/"):
                    old_filename = os.path.basename(old_avatar_url)
                    old_file_path = os.path.join(UPLOAD_DIR, old_filename)
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                            logger.info(f"Deleted old local avatar: {old_file_path}")
                        except Exception as e:
                            logger.warning(f"Error deleting old local avatar: {e}")
            else:
                logger.warning("Cloudinary upload failed, falling back to local storage")

        # Fallback to local storage if Cloudinary is not configured or failed
        if not avatar_url:
            logger.info("Using local storage for avatar upload")

            # Delete old local avatar if exists
            if current_user.avatar_url and current_user.avatar_url.startswith("/static/uploads/"):
                old_filename = os.path.basename(current_user.avatar_url)
                old_file_path = os.path.join(UPLOAD_DIR, old_filename)
                if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                    except Exception as e:
                        logger.warning(f"Error deleting old avatar: {e}")

            # Generate unique filename
            filename = file.filename or "avatar.png"
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            # Save file locally
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)

            avatar_url = f"/static/uploads/{unique_filename}"

        # Update user in database - use model_construct to set avatar_url directly
        user_update = UserUpdate.model_construct(avatar_url=avatar_url)
        updated_user = await user_service.update_user(current_user.id, user_update)

        logger.info(f"Avatar updated for user {current_user.id}: {avatar_url}")
        return updated_user  # type: ignore[return-value]

    except Exception as e:
        logger.error(f"Failed to upload avatar: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {e!s}",
        )
