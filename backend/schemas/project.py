"""
Project schemas for Insight-Flow application.
"""
from pydantic import BaseModel
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import uuid
from .user import UserResponse

class ProjectBase(BaseModel):
    """Base project schema."""
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    pass

class ProjectUpdate(BaseModel):
    """Schema for updating project information."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ProjectResponse(ProjectBase):
    """Schema for project response data."""
    id: uuid.UUID
    owner_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProjectMemberBase(BaseModel):
    """Base project member schema."""
    role: str

class ProjectMemberCreate(ProjectMemberBase):
    """Schema for creating a project member."""
    user_id: uuid.UUID

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