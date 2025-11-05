"""
Task history model for tracking task activities.
"""
from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class ActivityType(enum.Enum):
    """Enum for activity types."""
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_ASSIGNED = "task_assigned"
    TASK_UNASSIGNED = "task_unassigned"
    TASK_DELETED = "task_deleted"

class TaskHistory(BaseModel):
    """
    Task history model for tracking all task-related activities.
    """
    __tablename__ = "task_history"
    
    activity_type = Column(Enum(ActivityType), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    task_title = Column(String(255))
    description = Column(Text)
    old_values = Column(Text)  # JSON string of old values for updates
    new_values = Column(Text)  # JSON string of new values for updates
    timestamp = Column(DateTime(timezone=True), server_default='now()', index=True)
    
    # Relationships
    project = relationship("Project")
    task = relationship("Task")
    user = relationship("User")