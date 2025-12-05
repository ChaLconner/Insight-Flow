"""
User schemas for Insight-Flow application.
"""
from pydantic import BaseModel, EmailStr, field_validator, Field, model_validator, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import re
from utils.schema_utils import to_camel

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    name: Optional[str] = None  # Made optional to support first_name/last_name
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = Field(None, alias="avatar")
    phone: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: Optional[str] = None
    google_id: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
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
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
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
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = Field(None, alias="avatar")
    phone: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
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

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class UserResponse(UserBase):
    """Schema for user response data."""
    id: uuid.UUID
    is_active: bool
    role: str
    created_at: datetime
    updated_at: datetime
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email_verified: bool = True
    last_login_at: Optional[datetime] = None

    @field_validator('role', mode='before')
    @classmethod
    def set_default_role(cls, v: Optional[str]) -> str:
        return v or "user"
    
    @model_validator(mode='after')
    def compute_names(self) -> 'UserResponse':
        # If first_name and last_name are not provided but name is, split name
        if not self.first_name and not self.last_name and self.name:
            parts = self.name.split(" ", 1)
            self.first_name = parts[0]
            if len(parts) > 1:
                self.last_name = parts[1]
            else:
                self.last_name = ""
        
        # If first_name and last_name are provided but name is not, create name
        if self.first_name or self.last_name:
            self.name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        
        return self

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

class GoogleAuth(BaseModel):
    """Schema for Google authentication."""
    id_token: Optional[str] = None
    access_token: Optional[str] = None

class Token(BaseModel):
    """Schema for access token response."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

class UserSettingsBase(BaseModel):
    theme: Optional[str] = "dark"
    language: Optional[str] = "en"
    timezone: Optional[str] = "UTC"
    notification_preferences: Optional[Dict[str, Any]] = None
    working_hours_start: Optional[str] = "09:00"
    working_hours_end: Optional[str] = "17:00"

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class UserSettingsUpdate(UserSettingsBase):
    pass

class UserSettingsResponse(UserSettingsBase):
    user_id: uuid.UUID
    
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )