"""
Task history model for tracking task activities.
"""
from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class ActivityType(enum.Enum):
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