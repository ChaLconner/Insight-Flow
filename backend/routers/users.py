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
import uuid
import shutil
import os

router = APIRouter(prefix="/users", tags=["user management"])

UPLOAD_DIR = "static/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    q: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[UserResponse]:
    """
    Search users by email or name.
    """
    user_service = UserService(db)
    # The service might return all matching, we slice here for safety if service doesn't support pagination yet
    users = user_service.search_users(q)
    return users[skip : skip + limit]

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
    """
    try:
        # Delete old avatar if exists
        if current_user.avatar:
            old_avatar_path = current_user.avatar
            # Check if it's a local file (starts with /static/uploads/)
            if old_avatar_path.startswith("/static/uploads/"):
                filename = os.path.basename(old_avatar_path)
                file_path = os.path.join(UPLOAD_DIR, filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error deleting old avatar: {e}")

        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Create URL
        avatar_url = f"/static/uploads/{unique_filename}"
        
        # Update user in database
        user_service = UserService(db)
        # Create a partial update object
        user_update = UserUpdate(avatar=avatar_url)
        updated_user = user_service.update_user(current_user.id, user_update)
        
        return updated_user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}"
        )
