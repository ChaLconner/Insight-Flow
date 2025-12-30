"""
Notification schemas for Insight-Flow application.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from utils.schema_utils import to_camel


class NotificationBase(BaseModel):
    """Base notification schema."""

    type: str
    title: str
    message: str | None = None
    data: Any | None = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""

    user_id: uuid.UUID


class NotificationResponse(NotificationBase):
    """Schema for notification response data."""

    id: uuid.UUID
    user_id: uuid.UUID
    is_read: bool = Field(alias="read", serialization_alias="read")
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )
