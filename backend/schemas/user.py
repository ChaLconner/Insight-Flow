"""
User schemas for Insight-Flow application.
"""

import re
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from utils.schema_utils import to_camel


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str | None = None  # Made optional to support first_name/last_name
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    avatar_url: str | None = Field(None, alias="avatar")
    phone: str | None = None
    bio: str | None = None
    location: str | None = None
    website: str | None = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str | None = None
    google_id: str | None = None
    github_id: str | None = None
    plan: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate name field."""
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("ชื่อต้องมีอย่างน้อย 2 ตัวอักษร")
        if len(v) > 50:
            raise ValueError("ชื่อต้องไม่เกิน 50 ตัวอักษร")
        if not re.match(r"^[a-zA-Zก-๙\s]+$", v):
            raise ValueError("ชื่อสามารถใช้ได้เฉพาะตัวอักษรและเว้นวรรคเท่านั้น")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Validate email field."""
        if v is None:
            return v
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("รูปแบบอีเมลไม่ถูกต้อง")
        if len(v) > 254:
            raise ValueError("อีเมลต้องไม่เกิน 254 ตัวอักษร")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        """Validate password field."""
        if v is None:
            return v
        v = v.strip()
        if len(v) < 8:
            raise ValueError("รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
        if len(v) > 128:
            raise ValueError("รหัสผ่านต้องไม่เกิน 128 ตัวอักษร")

        return v


class UserInvite(BaseModel):
    """Schema for inviting a new user."""

    email: EmailStr
    role: str | None = "member"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email field."""
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    avatar_url: str | None = Field(None, alias="avatar")
    phone: str | None = None
    bio: str | None = None
    location: str | None = None
    website: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate name field."""
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("ชื่อต้องมีอย่างน้อย 2 ตัวอักษร")
        if len(v) > 50:
            raise ValueError("ชื่อต้องไม่เกิน 50 ตัวอักษร")
        if not re.match(r"^[a-zA-Zก-๙\s]+$", v):
            raise ValueError("ชื่อสามารถใช้ได้เฉพาะตัวอักษรและเว้นวรรคเท่านั้น")
        return v

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UserResponse(UserBase):
    """Schema for user response data."""

    id: uuid.UUID
    is_active: bool
    role: str
    created_at: datetime
    updated_at: datetime
    first_name: str | None = None
    last_name: str | None = None
    email_verified: bool = True
    last_login_at: datetime | None = None

    @field_validator("role", mode="before")
    @classmethod
    def set_default_role(cls, v: str | None) -> str:
        return v or "member"

    @model_validator(mode="after")
    def compute_names(self) -> "UserResponse":
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

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class GoogleAuth(BaseModel):
    """Schema for Google authentication."""

    id_token: str | None = None
    access_token: str | None = None


class GithubAuth(BaseModel):
    """Schema for GitHub authentication."""

    code: str | None = None  # Authorization code from GitHub OAuth redirect
    access_token: str | None = None  # Direct access token (if available)


class Token(BaseModel):
    """Schema for access token response."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserSettingsBase(BaseModel):
    theme: str | None = "dark"
    language: str | None = "en"
    timezone: str | None = "UTC"
    notification_preferences: dict[str, Any] | None = None
    working_hours_start: str | None = "09:00"
    working_hours_end: str | None = "17:00"

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UserSettingsUpdate(UserSettingsBase):
    pass


class UserSettingsResponse(UserSettingsBase):
    user_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class ResendVerificationRequest(BaseModel):
    """Schema for resending verification email."""

    email: EmailStr
