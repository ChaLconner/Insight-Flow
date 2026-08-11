import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import UUID, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel
from .base_enum import BaseEnum

CASCADE_DELETE_ORPHAN = "all, delete-orphan"

if TYPE_CHECKING:
    from .analytics import TaskAttachment, TaskComment, TaskDependency, TaskTimeTracking
    from .project import Project
    from .user import User


class TaskStatus(BaseEnum):
    """Enum for task status."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(BaseEnum):
    """Enum for task priority."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(BaseEnum):
    """Enum for task type."""

    FEATURE = "feature"
    BUG = "bug"
    IMPROVEMENT = "improvement"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    OTHER = "other"


class Task(BaseModel):
    """
    Task model representing project tasks.
    """

    __tablename__ = "tasks"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", values_callable=lambda obj: [e.value for e in obj]),
        default=TaskStatus.TODO,
        index=True,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(
            TaskPriority, name="task_priority", values_callable=lambda obj: [e.value for e in obj]
        ),
        default=TaskPriority.MEDIUM,
        index=True,
    )
    type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, name="task_type", values_callable=lambda obj: [e.value for e in obj]),
        default=TaskType.FEATURE,
        index=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assignee_id], back_populates="assigned_tasks"
    )
    creator: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by], back_populates="created_tasks"
    )
    comments: Mapped[list["TaskComment"]] = relationship(
        "TaskComment", back_populates="task", cascade=CASCADE_DELETE_ORPHAN
    )
    attachments: Mapped[list["TaskAttachment"]] = relationship(
        "TaskAttachment", back_populates="task", cascade=CASCADE_DELETE_ORPHAN
    )
    dependencies: Mapped[list["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade=CASCADE_DELETE_ORPHAN,
    )
    dependents: Mapped[list["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        back_populates="depends_on_task",
        cascade=CASCADE_DELETE_ORPHAN,
    )
    time_tracking: Mapped[list["TaskTimeTracking"]] = relationship(
        "TaskTimeTracking", back_populates="task", cascade=CASCADE_DELETE_ORPHAN
    )

    __table_args__ = (
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_project_status_priority", "project_id", "status", "priority"),
        Index("ix_tasks_assignee_status", "assignee_id", "status"),
        Index("ix_tasks_project_due_date", "project_id", "due_date"),
        Index("ix_tasks_project_updated_at", "project_id", "updated_at"),
        Index("ix_tasks_assignee_updated_at", "assignee_id", "updated_at"),
        Index(
            "ix_tasks_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index(
            "ix_tasks_description_trgm",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
    )

    def __init__(self, **kwargs):
        """Override __init__ to ensure UUID is generated immediately."""
        super().__init__(**kwargs)
        # Ensure ID is generated immediately
        if not self.id:
            import uuid

            self.id = uuid.uuid4()
