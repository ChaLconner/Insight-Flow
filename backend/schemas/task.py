"""
Task schemas for Insight-Flow application.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.task import TaskPriority, TaskType
from utils.schema_utils import to_camel
from utils.validators import validate_priority_value, validate_status_value, validate_type_value

from .project import ProjectSummary
from .user import UserResponse


class TaskBase(BaseModel):
    """Base task schema."""

    title: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    due_date: datetime | None = None
    priority: str | None = "medium"
    type: str | None = "feature"

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str:
        return validate_priority_value(v) or TaskPriority.MEDIUM.value

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str | None) -> str:
        return validate_type_value(v) or TaskType.FEATURE.value

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TaskCreate(TaskBase):
    """Schema for creating a new task."""

    project_id: uuid.UUID
    assignee_id: uuid.UUID | None = None
    status: str | None = "todo"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str:
        return validate_status_value(v) or "todo"

    model_config = ConfigDict(
        # Exclude id from creation schema - backend will generate it
        extra="forbid",
        alias_generator=to_camel,
        populate_by_name=True,
    )


class TaskUpdate(BaseModel):
    """Schema for updating task information."""

    title: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    status: str | None = None
    assignee_id: uuid.UUID | None = None
    due_date: datetime | None = None
    priority: str | None = None
    type: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        return validate_status_value(v)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        return validate_priority_value(v)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str | None) -> str | None:
        return validate_type_value(v)

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TaskStatusUpdate(BaseModel):
    """Schema for updating task status."""

    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        res = validate_status_value(v)
        if res is None:
            raise ValueError("Status is required")
        return res

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TaskAssign(BaseModel):
    """Schema for assigning task to user."""

    assignee_id: uuid.UUID

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TaskCommentCreate(BaseModel):
    """Schema for creating a task comment."""

    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        content = v.strip()
        if not content:
            raise ValueError("Comment content is required")
        return content

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TaskCommentResponse(BaseModel):
    """Schema for task comment response data."""

    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    is_edited: bool
    mentions: list[str]
    created_at: datetime
    updated_at: datetime
    user: UserResponse

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TaskResponse(TaskBase):
    """Schema for task response data."""

    id: uuid.UUID = Field(..., description="Task UUID")
    status: str
    project_id: uuid.UUID
    assignee_id: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class TaskWithDetails(TaskResponse):
    """Schema for task with related data included."""

    assignee: UserResponse | None = None
    creator: UserResponse
    project: ProjectSummary

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class TaskListResponse(BaseModel):
    """Schema for paginated task list response."""

    items: list[TaskWithDetails]
    total: int
    page: int
    size: int
    has_more: bool

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
