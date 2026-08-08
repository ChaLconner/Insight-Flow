"""
User management router for CRUD operations.
Refactored for Async operations with proper Dependency Injection.

Security features:
- Avatar upload validation (extension, MIME type, size)
- Role-based access control for sensitive endpoints
- Rate limiting integration
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status

from config import get_settings
from dependencies.services import get_user_service
from models.base_enum import UserRole
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
from utils.file_security import (
    AVATAR_MAX_FILE_SIZE_BYTES,
    FileSecurityError,
    read_upload_with_limit,
    validate_avatar_upload,
    validate_file_path,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["user management"])

# Route-level rate limiting for user operations
from rate_limiter import RateLimits, limiter

_settings = get_settings()
_configured_upload_dir = getattr(_settings, "upload_dir", None)
_default_upload_dir = Path(__file__).resolve().parent.parent / "static" / "uploads"
_upload_dir = Path(_configured_upload_dir) if _configured_upload_dir else _default_upload_dir
if not _upload_dir.is_absolute():
    _upload_dir = Path(__file__).resolve().parent.parent / _upload_dir
UPLOAD_DIR = str(_upload_dir)
os.makedirs(UPLOAD_DIR, exist_ok=True)
USER_ADMIN_ROLES = {UserRole.ADMIN, UserRole.MANAGER}
PRIVILEGED_INVITE_ROLES = {UserRole.ADMIN, UserRole.MANAGER}

# Initialize Cloudinary on module load
if is_cloudinary_configured():
    init_cloudinary()
    logger.info("Cloudinary initialized for avatar uploads")
else:
    logger.warning("Cloudinary not configured, falling back to local storage")


def _is_user_admin(user: User) -> bool:
    return getattr(user, "role", None) in USER_ADMIN_ROLES


def _require_user_admin(user: User) -> None:
    if not _is_user_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage users",
        )


def _query_matches_current_user(query: str, user: User) -> bool:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return False

    candidate_values = [
        getattr(user, "email", None),
        getattr(user, "name", None),
        getattr(user, "username", None),
    ]
    return any(normalized_query in str(value).lower() for value in candidate_values if value)


@router.get("/", response_model=list[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user_service: AsyncUserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get all users."""
    _require_user_admin(current_user)
    return await user_service.get_users(skip=skip, limit=limit)


@router.get("/stats")
async def get_user_stats(
    user_service: AsyncUserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get user statistics."""
    _require_user_admin(current_user)
    return await user_service.get_user_stats()


@router.post("/invite", response_model=UserResponse)
@limiter.limit(RateLimits.API_WRITE)
async def invite_user(
    request: Request,
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
    if current_user.role != "admin" and user_invite.role in PRIVILEGED_INVITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Managers cannot assign privileged roles",
        )

    try:
        user = await user_service.invite_user(user_invite, actor_role=current_user.role)
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
@limiter.limit(RateLimits.USER_PROFILE_UPDATE)
async def update_current_user_profile(
    request: Request,
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
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )


@router.get("/search/{email}", response_model=UserResponse)
@limiter.limit(RateLimits.USER_SEARCH)
async def search_user_by_email(
    request: Request,
    email: str,
    user_service: AsyncUserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Search user by email.

    Security: This endpoint is rate-limited and requires authentication.
    The current user must be admin/manager to search other users by exact email.
    Regular users can only search for their own email.
    """
    # Security: Regular users can only search for themselves
    if (
        current_user.role not in ["admin", "manager"]
        and email.lower() != current_user.email.lower()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to search other users"
        )

    user = await user_service.get_user_by_email(email)
    if not user:
        # Security: Use consistent error message to prevent email enumeration
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/search", response_model=list[UserResponse])
@limiter.limit(RateLimits.USER_SEARCH)
async def search_users(
    request: Request,
    q: str = "",
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    user_service: AsyncUserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Search users by email or name with filters.

    Security: Admins and managers can search all users.
    Regular users have limited search capabilities.
    """
    # Security: Limit what non-admin users can search
    if not _is_user_admin(current_user):
        # Non-admins can only do limited searches
        if role or status_filter:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to filter users",
            )
        if _query_matches_current_user(q, current_user):
            return [current_user]
        return []

    is_active = None
    if status_filter == "active":
        is_active = True
    elif status_filter == "inactive":
        is_active = False

    users = await user_service.search_users(
        q, skip=skip, limit=limit, role=role, is_active=is_active
    )
    return list(users)


@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_current_user_settings(
    current_user: User = Depends(get_current_active_user),
    user_service: AsyncUserService = Depends(get_user_service),
) -> Any:
    """Get current user settings."""
    return await user_service.get_or_create_settings(current_user.id)


@router.patch("/me/settings", response_model=UserSettingsResponse)
@limiter.limit(RateLimits.USER_PROFILE_UPDATE)
async def update_current_user_settings(
    request: Request,
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
@limiter.limit(RateLimits.USER_AVATAR)
async def upload_user_avatar(  # noqa: PLR0912, PLR0915
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    user_service: AsyncUserService = Depends(get_user_service),
) -> UserResponse:
    """
    Upload and update user avatar.
    Uses Cloudinary for cloud storage if configured, otherwise falls back to local storage.

    Security:
    - Only image files allowed (jpg, jpeg, png, gif, webp)
    - MIME type must match file extension
    - Maximum file size: 5 MB
    - Path traversal protection
    """
    new_local_path: str | None = None
    try:
        # Read in bounded chunks so oversized avatar bodies do not fill process memory.
        try:
            file_content = await read_upload_with_limit(file, AVATAR_MAX_FILE_SIZE_BYTES)
        except FileSecurityError as e:
            logger.warning(
                f"Avatar upload security violation for user {current_user.id}: {e.message}"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)

        # Security: Validate file upload (extension, MIME type, size)
        try:
            file_extension, _file_size = validate_avatar_upload(
                filename=file.filename,
                content_type=file.content_type,
                content=file_content,
            )
        except FileSecurityError as e:
            logger.warning(
                f"Avatar upload security violation for user {current_user.id}: {e.message}"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)

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

            else:
                logger.warning("Cloudinary upload failed, falling back to local storage")

        # Fallback to local storage if Cloudinary is not configured or failed
        if not avatar_url:
            logger.info("Using local storage for avatar upload")

            # Generate unique filename with validated extension
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            # Security: Validate final path
            validated_path = validate_file_path(UPLOAD_DIR, file_path)
            new_local_path = validated_path

            # Save file locally
            with open(validated_path, "wb") as buffer:
                buffer.write(file_content)

            avatar_url = f"/static/uploads/{unique_filename}"

        # Update user in database - use model_construct to set avatar_url directly
        user_update = UserUpdate.model_construct(avatar_url=avatar_url)
        updated_user = await user_service.update_user(current_user.id, user_update)
        committed_local_path = new_local_path
        # The local file is now referenced by the database and must not be
        # treated as an incomplete artifact if response handling raises later.
        new_local_path = None

        # Delete old local avatar only after the new database reference succeeds.
        if old_avatar_url and old_avatar_url.startswith("/static/uploads/"):
            old_filename = os.path.basename(old_avatar_url)
            old_file_path = os.path.join(UPLOAD_DIR, old_filename)
            try:
                validated_old_path = validate_file_path(UPLOAD_DIR, old_file_path)
                if (
                    os.path.exists(validated_old_path)
                    and validated_old_path != committed_local_path
                ):
                    os.remove(validated_old_path)
                    logger.info(f"Deleted old local avatar: {validated_old_path}")
            except Exception as e:
                logger.warning(f"Error deleting old local avatar: {e}")

        logger.info(f"Avatar updated for user {current_user.id}: {avatar_url}")
        return updated_user  # type: ignore[return-value]

    except HTTPException:
        if new_local_path and os.path.exists(new_local_path):
            try:
                os.remove(new_local_path)
            except OSError as cleanup_error:
                logger.warning(f"Failed to remove rejected avatar: {cleanup_error}")
        raise
    except Exception as e:
        if new_local_path and os.path.exists(new_local_path):
            try:
                os.remove(new_local_path)
            except OSError as cleanup_error:
                logger.warning(f"Failed to remove incomplete avatar: {cleanup_error}")
        logger.error(f"Failed to upload avatar: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar",
        )
