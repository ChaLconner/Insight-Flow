"""
User model for Insight-Flow application.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

CASCADE_DELETE_ORPHAN = "all, delete-orphan"

if TYPE_CHECKING:
    from .analytics import UserProductivity
    from .notification import Notification
    from .project import Project, ProjectMember
    from .task import Task, TaskAttachment, TaskComment, TaskTimeTracking
    from .user_favorite import UserFavorite
    from .user_settings import UserSettings


class User(BaseModel):
    """
    User model representing application users.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    github_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    # role field is optional to support existing databases without the field
    # will be set to default value "user" if not present
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Stripe customer ID (cached for faster payment operations)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Extended profile fields
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    owned_projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="owner", cascade=CASCADE_DELETE_ORPHAN
    )
    project_memberships: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="user", cascade=CASCADE_DELETE_ORPHAN
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task", foreign_keys="Task.assignee_id", back_populates="assignee"
    )
    created_tasks: Mapped[list["Task"]] = relationship(
        "Task", foreign_keys="Task.created_by", back_populates="creator"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade=CASCADE_DELETE_ORPHAN
    )
    productivity: Mapped[list["UserProductivity"]] = relationship(
        "UserProductivity", back_populates="user", cascade=CASCADE_DELETE_ORPHAN
    )
    time_tracking: Mapped[list["TaskTimeTracking"]] = relationship(
        "TaskTimeTracking", back_populates="user", cascade=CASCADE_DELETE_ORPHAN
    )
    task_comments: Mapped[list["TaskComment"]] = relationship(
        "TaskComment", back_populates="user", cascade=CASCADE_DELETE_ORPHAN
    )
    uploaded_attachments: Mapped[list["TaskAttachment"]] = relationship(
        "TaskAttachment", back_populates="uploaded_by_user", cascade=CASCADE_DELETE_ORPHAN
    )
    settings: Mapped[Optional["UserSettings"]] = relationship(
        "UserSettings", back_populates="user", uselist=False, cascade=CASCADE_DELETE_ORPHAN
    )
    favorite_projects: Mapped[list["UserFavorite"]] = relationship(
        "UserFavorite", back_populates="user", cascade=CASCADE_DELETE_ORPHAN
    )
