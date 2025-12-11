"""
User Settings model for Insight-Flow application.
"""
from sqlalchemy import Column, String, ForeignKey, JSON, UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class UserSettings(BaseModel):
    """
    User Settings model for storing user preferences.
    """
    __tablename__ = "user_settings"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Appearance
    theme = Column(String(20), default="dark") # light, dark, auto
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    
    # Notifications (JSON)
    notification_preferences = Column(JSON, nullable=True)
    
    # Working Hours
    working_hours_start = Column(String(5), default="09:00")
    working_hours_end = Column(String(5), default="17:00")
    
    user = relationship("User", back_populates="settings")
