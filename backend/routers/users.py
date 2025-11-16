"""
User management router for CRUD operations.
"""
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.user import UserResponse, UserCreate, UserUpdate
from models.user import User
from services.user_service import UserService
from database import get_db
from routers.auth import get_current_active_user

router = APIRouter(tags=["user management"])

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current user profile.
    """
    return current_user

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[UserResponse]:
    """
    Search users by email or name.
    """
    user_service = UserService(db)
    users = user_service.search_users(q)
    return users

