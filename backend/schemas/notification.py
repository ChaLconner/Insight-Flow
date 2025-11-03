"""
Notification schemas for Insight-Flow application.
"""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
import uuid

class NotificationBase(BaseModel):
    """Base notification schema."""
    type: str
    title: str
    message: Optional[str] = None
    data: Optional[Any] = None

class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""
    user_id: uuid.UUID

class NotificationResponse(NotificationBase):
    """Schema for notification response data."""
    id: uuid.UUID
    user_id: uuid.UUID
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True