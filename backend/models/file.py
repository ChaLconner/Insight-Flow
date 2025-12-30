"""
File model for tracking uploaded files and their metadata.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import UUID, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .user import User


class File(BaseModel):
    """
    File model for storing metadata about uploaded files.
    """

    __tablename__ = "files"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    unique_filename: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="files")
