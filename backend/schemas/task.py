"""
Task schemas for Insight-Flow application.
"""
from pydantic import BaseModel, Field, field_validator
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
    status: Optional[str] = "todo"  # Add status field with default value (lowercase to match database)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status value."""
        if v is not None:
            # Accept both lowercase and uppercase, but normalize to lowercase
            valid_statuses = ['todo', 'in_progress', 'done']
            if v.lower() not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower() if v else "todo"  # Normalize to lowercase
    
    class Config:
        # Exclude id from creation schema - backend will generate it
        extra = "forbid"

class TaskUpdate(BaseModel):
    """Schema for updating task information."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status value."""
        if v is not None:
            # Accept both lowercase and uppercase, but normalize to lowercase
            valid_statuses = ['todo', 'in_progress', 'done']
            if v.lower() not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower() if v else None  # Normalize to lowercase

class TaskStatusUpdate(BaseModel):
    """Schema for updating task status."""
    status: str
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status value."""
        if v is not None:
            # Accept both lowercase and uppercase, but normalize to lowercase
            valid_statuses = ['todo', 'in_progress', 'done']
            if v.lower() not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower()  # Normalize to lowercase

class TaskAssign(BaseModel):
    """Schema for assigning task to user."""
    assignee_id: uuid.UUID

class TaskResponse(TaskBase):
    """Schema for task response data."""
    id: uuid.UUID = Field(..., description="Task UUID")
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
    assignee: Optional[UserResponse] = None
    creator: UserResponse
    project: ProjectResponse
    
    model_config = {"from_attributes": True}