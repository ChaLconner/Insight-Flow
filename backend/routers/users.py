from typing import List, Any
"""
User management router for CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from schemas.user import UserResponse, UserCreate, UserUpdate, UserSettingsResponse, UserSettingsUpdate, UserInvite
from models.user import User
from models.user_settings import UserSettings
from services.user_service import UserService
from database import get_db
from routers.auth import get_current_active_user
from utils.cloudinary_upload import upload_avatar as cloudinary_upload_avatar, delete_avatar as cloudinary_delete_avatar, is_cloudinary_configured, init_cloudinary
import uuid
import shutil
import os
import logging

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

@router.get("/", response_model=List[UserResponse])
def get_users(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[UserResponse]:
    """
    Get all users.
    """
    user_service = UserService(db)
    return user_service.get_users(skip=skip, limit=limit)

@router.get("/stats")
def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Get user statistics.
    """
    user_service = UserService(db)
    return user_service.get_user_stats()

@router.post("/invite", response_model=UserResponse)
def invite_user(
    user_invite: UserInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Invite a new user.
    Only admins and managers can invite users.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to invite users"
        )

    user_service = UserService(db)
    try:
        user = user_service.invite_user(user_invite)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )



@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current user profile.
    """
    return current_user

@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Update current user profile.
    """
    try:
        user_service = UserService(db)
        updated_user = user_service.update_user(current_user.id, user_data)
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/search/{email}", response_model=UserResponse)
def search_user_by_email(
    email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Search user by email.
    """
    user_service = UserService(db)
    user = user_service.get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.get("/search", response_model=List[UserResponse])
def search_users(
    q: str = "",
    skip: int = 0,
    limit: int = 20,
    role: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[UserResponse]:
    """
    Search users by email or name with filters.
    """
    user_service = UserService(db)
    
    is_active = None
    if status == "active":
        is_active = True
    elif status == "inactive":
        is_active = False
        
    users = user_service.search_users(q, skip=skip, limit=limit, role=role, is_active=is_active)
    return users

@router.get("/me/settings", response_model=UserSettingsResponse)
def get_current_user_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserSettingsResponse:
    """
    Get current user settings.
    """
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        # Create default settings if not exists
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.patch("/me/settings", response_model=UserSettingsResponse)
def update_current_user_settings(
    settings_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserSettingsResponse:
    """
    Update current user settings.
    """
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    
    update_data = settings_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    return settings


@router.post("/me/avatar", response_model=UserResponse)
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Upload and update user avatar.
    Uses Cloudinary for cloud storage if configured, otherwise falls back to local storage.
    """
    try:
        # Read file content
        file_content = await file.read()
        avatar_url = None
        old_avatar_url = current_user.avatar_url
        
        # Try Cloudinary upload first
        if is_cloudinary_configured():
            logger.info(f"Uploading avatar to Cloudinary for user {current_user.id}")
            
            # Delete old Cloudinary avatar if exists (to prevent storage bloat)
            # Note: Since we use overwrite=True with same public_id, this is automatic
            # But we log it for clarity
            if old_avatar_url and "res.cloudinary.com" in old_avatar_url:
                logger.info(f"Old Cloudinary avatar will be replaced: {old_avatar_url}")
            
            result = cloudinary_upload_avatar(
                file_content=file_content,
                filename=file.filename,
                user_id=str(current_user.id)
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
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            # Save file locally
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
                
            avatar_url = f"/static/uploads/{unique_filename}"
        
        # Update user in database
        user_service = UserService(db)
        user_update = UserUpdate(avatar_url=avatar_url)
        updated_user = user_service.update_user(current_user.id, user_update)
        
        logger.info(f"Avatar updated for user {current_user.id}: {avatar_url}")
        return updated_user
        
    except Exception as e:
        logger.error(f"Failed to upload avatar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}"
        )

