import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, UUID, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .project import Project
    from .task import Task
    from .user import User


class AnalyticsPeriod(str, enum.Enum):
    """Enum for analytics periods."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ProjectAnalytics(BaseModel):
    """
    ProjectAnalytics model for storing pre-computed project analytics.
    """

    __tablename__ = "project_analytics"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Task statistics
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    todo_tasks: Mapped[int] = mapped_column(Integer, default=0)
    in_progress_tasks: Mapped[int] = mapped_column(Integer, default=0)

    # Productivity metrics
    productivity_score: Mapped[float] = mapped_column(Float, default=0.0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    average_completion_time: Mapped[float | None] = mapped_column(Float)  # in hours

    # Member activity
    active_members: Mapped[int] = mapped_column(Integer, default=0)
    total_activities: Mapped[int] = mapped_column(Integer, default=0)

    # Additional metrics stored as JSON
    metrics_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="analytics")


class UserProductivity(BaseModel):
    """
    UserProductivity model for tracking user productivity over time.
    """

    __tablename__ = "user_productivity"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Task statistics
    tasks_created: Mapped[int] = mapped_column(Integer, default=0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_assigned: Mapped[int] = mapped_column(Integer, default=0)

    # Time tracking
    total_time_spent: Mapped[float | None] = mapped_column(Float)  # in hours
    average_completion_time: Mapped[float | None] = mapped_column(Float)  # in hours

    # Productivity score
    productivity_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="productivity")
    project: Mapped["Project"] = relationship("Project", back_populates="user_productivity")


class TaskTimeTracking(BaseModel):
    """
    TaskTimeTracking model for tracking time spent on tasks.
    """

    __tablename__ = "task_time_tracking"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Time tracking
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)

    # Status tracking
    is_active: Mapped[str] = mapped_column(String(20), default="active")

    # Notes
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="time_tracking")
    user: Mapped["User"] = relationship("User", back_populates="time_tracking")


class ProjectMilestone(BaseModel):
    """
    ProjectMilestone model for tracking project milestones.
    """

    __tablename__ = "project_milestones"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Dates
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Status
    is_completed: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, completed, cancelled
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="milestones")


class TaskDependency(BaseModel):
    """
    TaskDependency model for managing task dependencies.
    """

    __tablename__ = "task_dependencies"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True
    )
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True
    )
    dependency_type: Mapped[str] = mapped_column(String(20), default="finish_to_start")

    # Relationships
    task: Mapped["Task"] = relationship(
        "Task", foreign_keys="TaskDependency.task_id", back_populates="dependencies"
    )
    depends_on_task: Mapped["Task"] = relationship(
        "Task", foreign_keys="TaskDependency.depends_on_task_id", back_populates="dependents"
    )


class TaskComment(BaseModel):
    """
    TaskComment model for task comments and discussions.
    """

    __tablename__ = "task_comments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Comment metadata
    is_edited: Mapped[str] = mapped_column(String(10), default="false")
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="comments")
    user: Mapped["User"] = relationship("User", back_populates="task_comments")


class TaskAttachment(BaseModel):
    """
    TaskAttachment model for file attachments to tasks.
    """

    __tablename__ = "task_attachments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer)
    file_type: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="attachments")
    uploaded_by_user: Mapped["User"] = relationship("User", back_populates="uploaded_attachments")


class ProjectTag(BaseModel):
    """
    ProjectTag model for categorizing projects.
    """

    __tablename__ = "project_tags"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    color: Mapped[str | None] = mapped_column(String(7))  # hex color code
    description: Mapped[str | None] = mapped_column(Text)

    # Relationships
    project_associations: Mapped[list["ProjectTagAssociation"]] = relationship(
        "ProjectTagAssociation", back_populates="tag"
    )


class ProjectTagAssociation(BaseModel):
    """
    ProjectTagAssociation model for many-to-many relationship between projects and tags.
    """

    __tablename__ = "project_tag_associations"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_tags.id"), nullable=False, index=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tag_associations")
    tag: Mapped["ProjectTag"] = relationship("ProjectTag", back_populates="project_associations")
