"""Add per-user session version for password-change revocation.

Revision ID: h1i2j3k4l5m6
Revises: g0b1c2d3e4f5
Create Date: 2026-08-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "h1i2j3k4l5m6"
down_revision: str | Sequence[str] | None = "g0b1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS session_version INTEGER NOT NULL DEFAULT 0
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS session_version")
