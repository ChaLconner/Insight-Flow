"""
Task schemas for Insight-Flow application.
"""
from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING
from datetime import datetime
import uuid
from .user import UserResponse
from .project import ProjectResponse

class TaskBase(BaseModel):
    """Base task schema."""
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    project_id: uuid.UUID
    assignee_id: Optional[uuid.UUID] = None

class TaskUpdate(BaseModel):
    """Schema for updating task information."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None

class TaskStatusUpdate(BaseModel):
    """Schema for updating task status."""
    status: str

class TaskAssign(BaseModel):
    """Schema for assigning task to user."""
    assignee_id: uuid.UUID

class TaskResponse(TaskBase):
    """Schema for task response data."""
    id: uuid.UUID
    status: str
    project_id: uuid.UUID
    assignee_id: Optional[uuid.UUID]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TaskWithDetails(TaskResponse):
    """Schema for task with related data included."""
    assignee: Optional['UserResponse']
    creator: 'UserResponse'
    project: 'ProjectResponse'