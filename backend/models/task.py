from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, Text, Enum, Index
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class TaskStatus(str, enum.Enum):
    """Enum for task status."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"

class TaskPriority(str, enum.Enum):
    """Enum for task priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskType(str, enum.Enum):
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
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus, name="task_status", values_callable=lambda obj: [e.value for e in obj]), default=TaskStatus.TODO, index=True)
    priority = Column(Enum(TaskPriority, name="task_priority", values_callable=lambda obj: [e.value for e in obj]), default=TaskPriority.MEDIUM, index=True)
    type = Column(Enum(TaskType, name="task_type", values_callable=lambda obj: [e.value for e in obj]), default=TaskType.FEATURE, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_tasks")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")
    dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.task_id", back_populates="task", cascade="all, delete-orphan")
    dependents = relationship("TaskDependency", foreign_keys="TaskDependency.depends_on_task_id", back_populates="depends_on_task", cascade="all, delete-orphan")
    time_tracking = relationship("TaskTimeTracking", back_populates="task", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_tasks_project_status', 'project_id', 'status'),
    )

    def __init__(self, **kwargs):
        """Override __init__ to ensure UUID is generated immediately."""
        super().__init__(**kwargs)
        # Ensure ID is generated immediately
        if not self.id:
            import uuid
            self.id = uuid.uuid4()
