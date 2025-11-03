"""
Task model for Insight-Flow application.
"""
from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class TaskStatus(enum.Enum):
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
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    due_date = Column(DateTime(timezone=True), index=True)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[Task.assignee_id], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[Task.created_by], back_populates="created_tasks")