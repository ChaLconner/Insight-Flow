"""
Notification model for Insight-Flow application.
"""

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, UUID, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .user import User


class NotificationType(str, enum.Enum):
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

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")

    from sqlalchemy import Index

    __table_args__ = (
        Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),
    )
