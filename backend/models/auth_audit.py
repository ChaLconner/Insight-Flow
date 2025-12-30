"""
Audit log model for tracking authentication events.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import UUID, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .user import User


class AuthStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    LOCKED = "locked"


class AuthAudit(BaseModel):
    """
    Model for storing authentication audit logs.
    """

    __tablename__ = "auth_audits"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Store email in case user_id is null (user not found)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # success, failure, locked
    attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Optional relationship
    user: Mapped[Optional["User"]] = relationship("User", backref="auth_audits")
