"""
User Favorite model for storing user's favorite projects.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import UUID, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .project import Project
    from .user import User


class UserFavorite(BaseModel):
    """
    UserFavorite model representing many-to-many relationship
    between users and their favorite projects.
    """

    __tablename__ = "user_favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="favorite_projects")
    project: Mapped["Project"] = relationship("Project", back_populates="favorited_by")

    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_user_favorites_user_project"),
    )
