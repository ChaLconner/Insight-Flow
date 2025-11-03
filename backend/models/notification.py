"""
Notification model for Insight-Flow application.
"""
from sqlalchemy import Column, String, UUID, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class NotificationType(enum.Enum):
    """Enum for notification types."""
    TASK_ASSIGNED = "task_assigned"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    PROJECT_INVITATION = "project_invitation"
    PROJECT_MEMBER_JOINED = "project_member_joined"
    PROJECT_MEMBER_LEFT = "project_member_left"

class Notification(BaseModel):
    """
    Notification model representing user notifications.
    """
    __tablename__ = "notifications"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    data = Column(JSON)
    is_read = Column(Boolean, default=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")