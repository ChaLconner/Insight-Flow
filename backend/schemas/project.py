"""
Project schemas for Insight-Flow application.
"""

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.project import MemberRole
from utils.schema_utils import to_camel

from .user import UserResponse  # noqa: TC001 - Required at runtime for Pydantic


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    color: str = Field(default="#6366f1", min_length=7, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")
    settings: dict[str, Any] = Field(default_factory=dict, max_length=100)

    @field_validator("settings")
    @classmethod
    def validate_settings_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value, ensure_ascii=False)) > 32_768:
            raise ValueError("Project settings are too large")
        return value

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    members: list["ProjectMemberCreate"] | None = Field(None, max_length=50)

    def __init__(self, **data: Any) -> None:
        # Handle None or empty members
        if "members" not in data or data["members"] is None:
            data["members"] = []
        super().__init__(**data)

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProjectUpdate(BaseModel):
    """Schema for updating project information."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    color: str | None = Field(
        default=None, min_length=7, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$"
    )
    settings: dict[str, Any] | None = Field(None, max_length=100)
    is_active: bool | None = None
    member_ids: list[uuid.UUID] | None = Field(None, max_length=50)

    @field_validator("settings")
    @classmethod
    def validate_update_settings_size(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None and len(json.dumps(value, ensure_ascii=False)) > 32_768:
            raise ValueError("Project settings are too large")
        return value

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProjectMemberSummary(BaseModel):
    """Schema for project member summary in project list."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    email: str
    avatar_url: str | None = Field(None, alias="avatar")
    role: str

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class ProjectMemberBase(BaseModel):
    """Base project member schema."""

    role: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProjectResponse(ProjectBase):
    """Schema for project response."""

    id: uuid.UUID
    owner_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    task_count: int | None = 0
    completed_tasks: int | None = 0
    overdue_tasks: int | None = 0
    recent_activity: int | None = 0
    member_count: int | None = 0
    member_summaries: list[ProjectMemberSummary] = []

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class ProjectMemberCreate(ProjectMemberBase):
    """Schema for creating a project member."""

    user_id: str  # Accept string UUID from frontend
    role: str = "member"  # Default role is member

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        # Validate role only if role is provided
        if self.role:
            valid_roles = [MemberRole.ADMIN.value, MemberRole.MEMBER.value]
            if self.role not in valid_roles:
                raise ValueError(f"Invalid member role. Must be one of: {valid_roles}")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProjectMemberResponse(ProjectMemberBase):
    """Schema for project member response data."""

    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime
    user: "UserResponse"

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class ProjectWithMembers(ProjectResponse):
    """Schema for project with members included."""

    members: list[ProjectMemberResponse]

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class ProjectSummary(ProjectBase):
    """Schema for project summary in task list."""

    id: uuid.UUID
    owner_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("color", mode="before")
    @classmethod
    def normalize_legacy_color(cls, value: Any) -> Any:
        """Keep task responses compatible with legacy project rows/mocks."""
        return value if isinstance(value, str) else "#6366f1"

    @field_validator("settings", mode="before")
    @classmethod
    def normalize_legacy_settings(cls, value: Any) -> dict[str, Any]:
        """Keep task responses compatible with legacy project rows/mocks."""
        return value if isinstance(value, dict) else {}

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)
