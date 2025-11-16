"""
Task model for Insight-Flow application.
"""
from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class TaskStatus(str, enum.Enum):
    """Enum for task status."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class Task(BaseModel):
    """
    Task model representing project tasks.
    """
    __tablename__ = "tasks"
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(TaskStatus, values_callable=lambda x: [e.value for e in TaskStatus]), default=TaskStatus.TODO, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    due_date = Column(DateTime(timezone=True), index=True)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_tasks")
    time_tracking = relationship("TaskTimeTracking", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")
    dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.task_id", back_populates="task", cascade="all, delete-orphan")
    dependents = relationship("TaskDependency", foreign_keys="TaskDependency.depends_on_task_id", back_populates="depends_on_task", cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        """Override __init__ to ensure UUID is generated immediately."""
        super().__init__(**kwargs)
        # Ensure ID is generated immediately
        if not self.id:
            import uuid
            self.id = uuid.uuid4()