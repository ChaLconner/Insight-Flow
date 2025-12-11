"""
Notification schemas for Insight-Flow application.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime
import uuid
from utils.schema_utils import to_camel

class NotificationBase(BaseModel):
    """Base notification schema."""
    type: str
    title: str
    message: Optional[str] = None
    data: Optional[Any] = None
    
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""
    user_id: uuid.UUID

class NotificationResponse(NotificationBase):
    """Schema for notification response data."""
    id: uuid.UUID
    user_id: uuid.UUID
    is_read: bool
    created_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )