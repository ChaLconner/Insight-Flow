"""
User schemas for Insight-Flow application.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: Optional[str] = None
    google_id: Optional[str] = None

class UserUpdate(BaseModel):
    """Schema for updating user information."""
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    """Schema for user response data."""
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

class GoogleAuth(BaseModel):
    """Schema for Google authentication."""
    id_token: str

class Token(BaseModel):
    """Schema for access token response."""
    access_token: str
    token_type: str
    expires_in: int