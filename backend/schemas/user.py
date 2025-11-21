"""
User schemas for Insight-Flow application.
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import uuid
import re

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: Optional[str] = None
    google_id: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate name field."""
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError('ชื่อต้องมีอย่างน้อย 2 ตัวอักษร')
        if len(v) > 50:
            raise ValueError('ชื่อต้องไม่เกิน 50 ตัวอักษร')
        if not re.match(r"^[a-zA-Zก-๙\s]+$", v):
            raise ValueError('ชื่อสามารถใช้ได้เฉพาะตัวอักษรและเว้นวรรคเท่านั้น')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email field."""
        if v is None:
            return v
        v = v.strip().lower()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('รูปแบบอีเมลไม่ถูกต้อง')
        if len(v) > 254:
            raise ValueError('อีเมลต้องไม่เกิน 254 ตัวอักษร')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password field."""
        if v is None:
            return v
        v = v.strip()
        if len(v) < 8:
            raise ValueError('รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร')
        if len(v) > 128:
            raise ValueError('รหัสผ่านต้องไม่เกิน 128 ตัวอักษร')
        if not re.search(r'[A-Z]', v):
            raise ValueError('รหัสผ่านต้องมีตัวพิมพ์ใหญ่อย่างน้อย 1 ตัว')
        if not re.search(r'[a-z]', v):
            raise ValueError('รหัสผ่านต้องมีตัวพิมพ์เล็กอย่างน้อย 1 ตัว')
        if not re.search(r'[0-9]', v):
            raise ValueError('รหัสผ่านต้องมีตัวเลขอย่างน้อย 1 ตัว')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว')
        return v

class UserUpdate(BaseModel):
    """Schema for updating user information."""
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate name field."""
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError('ชื่อต้องมีอย่างน้อย 2 ตัวอักษร')
        if len(v) > 50:
            raise ValueError('ชื่อต้องไม่เกิน 50 ตัวอักษร')
        if not re.match(r"^[a-zA-Zก-๙\s]+$", v):
            raise ValueError('ชื่อสามารถใช้ได้เฉพาะตัวอักษรและเว้นวรรคเท่านั้น')
        return v

class UserResponse(UserBase):
    """Schema for user response data."""
    id: uuid.UUID
    is_active: bool
    role: str
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
    refresh_token: str
    token_type: str
    expires_in: int