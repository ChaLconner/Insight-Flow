"""
Project models for Insight-Flow application.
"""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import BaseModel

if TYPE_CHECKING:
    from .analytics import (
        ProjectAnalytics,
        ProjectMilestone,
        ProjectTagAssociation,
        UserProductivity,
    )
    from .task import Task
    from .user import User
    from .user_favorite import UserFavorite


class Project(BaseModel):
    """
    Project model representing team projects.
    """

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="owned_projects")
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )
    analytics: Mapped[list["ProjectAnalytics"]] = relationship(
        "ProjectAnalytics", back_populates="project", cascade="all, delete-orphan"
    )
    user_productivity: Mapped[list["UserProductivity"]] = relationship(
        "UserProductivity", back_populates="project", cascade="all, delete-orphan"
    )
    milestones: Mapped[list["ProjectMilestone"]] = relationship(
        "ProjectMilestone", back_populates="project", cascade="all, delete-orphan"
    )
    tag_associations: Mapped[list["ProjectTagAssociation"]] = relationship(
        "ProjectTagAssociation", back_populates="project", cascade="all, delete-orphan"
    )
    favorited_by: Mapped[list["UserFavorite"]] = relationship(
        "UserFavorite", back_populates="project", cascade="all, delete-orphan"
    )


class MemberRole(str, enum.Enum):
    """Enum for project member roles."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class ProjectMember(BaseModel):
    """
    ProjectMember model representing many-to-many relationship between users and projects.
    """

    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=MemberRole.MEMBER.value)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="project_memberships")

    from sqlalchemy import Index

    __table_args__ = (
        Index("ix_project_members_project_user", "project_id", "user_id"),
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )
