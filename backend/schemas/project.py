"""
Project schemas for Insight-Flow application.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
import uuid
from .user import UserResponse
from models.project import MemberRole
from utils.schema_utils import to_camel

class ProjectBase(BaseModel):
    """Base project schema."""
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    members: Optional[List['ProjectMemberCreate']] = None
    
    def __init__(self, **data: Any) -> None:
        # Handle None or empty members
        if 'members' not in data or data['members'] is None:
            data['members'] = []
        super().__init__(**data)
    
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class ProjectUpdate(BaseModel):
    """Schema for updating project information."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class ProjectMemberSummary(BaseModel):
    """Schema for project member summary in project list."""
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    email: str
    avatar_url: Optional[str] = Field(None, alias="avatar")
    role: str
    
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )

class ProjectMemberBase(BaseModel):
    """Base project member schema."""
    role: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: uuid.UUID
    owner_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    task_count: Optional[int] = 0
    completed_tasks: Optional[int] = 0
    overdue_tasks: Optional[int] = 0
    recent_activity: Optional[int] = 0
    member_count: Optional[int] = 0
    member_summaries: List[ProjectMemberSummary] = []

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )

class ProjectMemberCreate(ProjectMemberBase):
    """Schema for creating a project member."""
    user_id: str  # Accept string UUID from frontend
    role: str = "member"  # Default role is member
    
    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        # Validate role only if role is provided
        if self.role:
            valid_roles = [MemberRole.OWNER.value, MemberRole.ADMIN.value, MemberRole.MEMBER.value]
            if self.role not in valid_roles:
                raise ValueError(f"Invalid role. Must be one of: {valid_roles}")
    
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class ProjectMemberResponse(ProjectMemberBase):
    """Schema for project member response data."""
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime
    user: 'UserResponse'
    
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )

class ProjectWithMembers(ProjectResponse):
    """Schema for project with members included."""
    members: List[ProjectMemberResponse]
    
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )

class ProjectSummary(ProjectBase):
    """Schema for project summary in task list."""
    id: uuid.UUID
    owner_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )