"""
User Settings model for Insight-Flow application.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, UUID, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .user import User


class UserSettings(BaseModel):
    """
    User Settings model for storing user preferences.
    """

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True
    )

    # Appearance
    theme: Mapped[str] = mapped_column(String(20), default="dark")  # light, dark, auto
    language: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    # Notifications (JSON)
    notification_preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Working Hours
    working_hours_start: Mapped[str] = mapped_column(String(5), default="09:00")
    working_hours_end: Mapped[str] = mapped_column(String(5), default="17:00")

    user: Mapped["User"] = relationship("User", back_populates="settings")
