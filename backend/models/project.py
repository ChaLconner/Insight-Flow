"""
Project models for Insight-Flow application.
"""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, UUID, Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import BaseModel

CASCADE_DELETE_ORPHAN = "all, delete-orphan"

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
    color: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#6366f1", server_default="#6366f1"
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="owned_projects")
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project", cascade=CASCADE_DELETE_ORPHAN
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="project", cascade=CASCADE_DELETE_ORPHAN
    )
    analytics: Mapped[list["ProjectAnalytics"]] = relationship(
        "ProjectAnalytics", back_populates="project", cascade=CASCADE_DELETE_ORPHAN
    )
    user_productivity: Mapped[list["UserProductivity"]] = relationship(
        "UserProductivity", back_populates="project", cascade=CASCADE_DELETE_ORPHAN
    )
    milestones: Mapped[list["ProjectMilestone"]] = relationship(
        "ProjectMilestone", back_populates="project", cascade=CASCADE_DELETE_ORPHAN
    )
    tag_associations: Mapped[list["ProjectTagAssociation"]] = relationship(
        "ProjectTagAssociation", back_populates="project", cascade=CASCADE_DELETE_ORPHAN
    )
    favorited_by: Mapped[list["UserFavorite"]] = relationship(
        "UserFavorite", back_populates="project", cascade=CASCADE_DELETE_ORPHAN
    )

    __table_args__ = (
        Index(
            "ix_projects_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_projects_description_trgm",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
        Index("ix_projects_owner_created_at", "owner_id", "created_at"),
        Index("ix_projects_owner_is_active", "owner_id", "is_active"),
    )


class MemberRole(enum.StrEnum):
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

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        Index("ix_project_members_project_created_at", "project_id", "created_at"),
    )
