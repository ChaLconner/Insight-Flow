"""
Task schemas for Insight-Flow application.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Any, List
from datetime import datetime
import uuid
from .user import UserResponse
from .project import ProjectResponse, ProjectSummary
from utils.schema_utils import to_camel
from models.task import TaskPriority, TaskType

class TaskBase(BaseModel):
    """Base task schema."""
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = "medium"
    type: Optional[str] = "feature"
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> str:
        if v:
            try:
                return TaskPriority(v.lower()).value
            except ValueError:
                # raising strings in ValueError is safer for pydantic serialization if custom handler exists
                raise ValueError(f"Priority must be one of: {', '.join([e.value for e in TaskPriority])}")
        return TaskPriority.MEDIUM.value

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: Optional[str]) -> str:
        if v:
            try:
                return TaskType(v.lower()).value
            except ValueError:
                raise ValueError(f"Type must be one of: {', '.join([e.value for e in TaskType])}")
        return TaskType.FEATURE.value

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    project_id: uuid.UUID
    assignee_id: Optional[uuid.UUID] = None
    status: Optional[str] = "todo"
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> str:
        """Validate status value."""
        if v is not None:
            # Accept both lowercase and uppercase, but normalize to lowercase
            valid_statuses = ['todo', 'in_progress', 'in_review', 'done', 'cancelled']
            if v.lower() not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower() if v else "todo"  # Normalize to lowercase
    
    model_config = ConfigDict(
        # Exclude id from creation schema - backend will generate it
        extra="forbid",
        alias_generator=to_camel,
        populate_by_name=True
    )

class TaskUpdate(BaseModel):
    """Schema for updating task information."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    type: Optional[str] = None
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status value."""
        if v is not None:
            # Accept both lowercase and uppercase, but normalize to lowercase
            valid_statuses = ['todo', 'in_progress', 'in_review', 'done', 'cancelled']
            if v.lower() not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower() if v else None  # Normalize to lowercase

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                return TaskPriority(v.lower()).value
            except ValueError:
                # raising strings in ValueError is safer for pydantic serialization if custom handler exists
                raise ValueError(f"Priority must be one of: {', '.join([e.value for e in TaskPriority])}")
        return None

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                return TaskType(v.lower()).value
            except ValueError:
                raise ValueError(f"Type must be one of: {', '.join([e.value for e in TaskType])}")
        return None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class TaskStatusUpdate(BaseModel):
    """Schema for updating task status."""
    status: str
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        if v is not None:
            # Accept both lowercase and uppercase, but normalize to lowercase
            valid_statuses = ['todo', 'in_progress', 'in_review', 'done', 'cancelled']
            if v.lower() not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower()  # Normalize to lowercase

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class TaskAssign(BaseModel):
    """Schema for assigning task to user."""
    assignee_id: uuid.UUID

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class TaskResponse(TaskBase):
    """Schema for task response data."""
    id: uuid.UUID = Field(..., description="Task UUID")
    status: str
    project_id: uuid.UUID
    assignee_id: Optional[uuid.UUID]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )

class TaskWithDetails(TaskResponse):
    """Schema for task with related data included."""
    assignee: Optional[UserResponse] = None
    creator: UserResponse
    project: ProjectSummary
    
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )

class TaskListResponse(BaseModel):
    """Schema for paginated task list response."""
    items: List[TaskWithDetails]
    total: int
    page: int
    size: int
    has_more: bool
    
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )