"""
Project schemas for Insight-Flow application.
"""
from pydantic import BaseModel
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import uuid
from .user import UserResponse
from models.project import MemberRole

class ProjectBase(BaseModel):
    """Base project schema."""
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    members: Optional[List['ProjectMemberCreate']] = None
    
    def __init__(self, **data):
        # Handle None or empty members
        if 'members' not in data or data['members'] is None:
            data['members'] = []
        super().__init__(**data)

class ProjectUpdate(BaseModel):
    """Schema for updating project information."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ProjectMemberSummary(BaseModel):
    """Schema for project member summary in project list."""
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    email: str
    avatar_url: Optional[str] = None
    role: str
    
    class Config:
        from_attributes = True

class ProjectResponse(ProjectBase):
    """Schema for project response data."""
    id: uuid.UUID
    owner_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    task_count: Optional[int] = 0
    completed_tasks: Optional[int] = 0
    member_count: Optional[int] = 0
    member_summaries: Optional[List[ProjectMemberSummary]] = []
    
    class Config:
        from_attributes = True

class ProjectMemberBase(BaseModel):
    """Base project member schema."""
    role: str

class ProjectMemberCreate(ProjectMemberBase):
    """Schema for creating a project member."""
    user_id: str  # Accept string UUID from frontend
    role: str = "member"  # Default role is member
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate role only if role is provided
        if self.role:
            valid_roles = [MemberRole.OWNER.value, MemberRole.ADMIN.value, MemberRole.MEMBER.value]
            if self.role not in valid_roles:
                raise ValueError(f"Invalid role. Must be one of: {valid_roles}")

class ProjectMemberResponse(ProjectMemberBase):
    """Schema for project member response data."""
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime
    user: 'UserResponse'
    
    class Config:
        from_attributes = True

class ProjectWithMembers(ProjectResponse):
    """Schema for project with members included."""
    members: List[ProjectMemberResponse]