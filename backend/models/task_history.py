import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import BaseModel
from .base_enum import BaseEnum

if TYPE_CHECKING:
    from .project import Project
    from .task import Task
    from .user import User


class ActivityType(BaseEnum):
    """Enum for activity types."""

    TASK_CREATED = "TASK_CREATED"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_UNASSIGNED = "TASK_UNASSIGNED"
    TASK_DELETED = "TASK_DELETED"
    PROJECT_MEMBER_ADDED = "PROJECT_MEMBER_ADDED"
    PROJECT_MEMBER_REMOVED = "PROJECT_MEMBER_REMOVED"
    PROJECT_MEMBER_ROLE_CHANGED = "PROJECT_MEMBER_ROLE_CHANGED"
    PROJECT_UPDATED = "PROJECT_UPDATED"
    PROJECT_CREATED = "PROJECT_CREATED"


class TaskHistory(BaseModel):
    """
    Task history model for tracking all task-related activities.
    """

    __tablename__ = "task_history"

    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    task_title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    old_values: Mapped[str | None] = mapped_column(Text)  # JSON string of old values for updates
    new_values: Mapped[str | None] = mapped_column(Text)  # JSON string of new values for updates
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    task: Mapped["Task"] = relationship("Task")
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("ix_task_history_project_timestamp", "project_id", "timestamp"),
        Index(
            "ix_task_history_project_activity_timestamp",
            "project_id",
            "activity_type",
            "timestamp",
        ),
        Index("ix_task_history_user_activity_timestamp", "user_id", "activity_type", "timestamp"),
        Index("ix_task_history_task_id_created_at", "task_id", "created_at"),
    )
