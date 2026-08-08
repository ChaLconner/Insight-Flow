"""Align remaining live metadata drift after schema reconciliation.

Revision ID: f9a0b1c2d3e4
Revises: e7f8a9b0c1d2
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9a0b1c2d3e4"
down_revision: str | Sequence[str] | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Align JSON storage and store expiry timestamps with explicit UTC semantics."""
    op.execute("ALTER TABLE projects ALTER COLUMN settings DROP DEFAULT")
    op.execute("ALTER TABLE projects ALTER COLUMN settings TYPE JSONB USING settings::jsonb")
    op.execute("ALTER TABLE projects ALTER COLUMN settings SET DEFAULT '{}'::jsonb")

    op.alter_column(
        "security_logs",
        "details",
        existing_type=postgresql.JSON(),
        type_=postgresql.JSONB(),
        postgresql_using="details::jsonb",
    )

    op.alter_column(
        "password_resets",
        "expires_at",
        existing_type=sa.DateTime(timezone=False),
        type_=sa.DateTime(timezone=True),
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    """Revert aligned storage to the pre-reconciliation representations."""
    op.execute("ALTER TABLE projects ALTER COLUMN settings DROP DEFAULT")
    op.execute("ALTER TABLE projects ALTER COLUMN settings TYPE JSON USING settings::json")
    op.execute("ALTER TABLE projects ALTER COLUMN settings SET DEFAULT '{}'")

    op.alter_column(
        "security_logs",
        "details",
        existing_type=postgresql.JSONB(),
        type_=postgresql.JSON(),
        postgresql_using="details::json",
    )

    op.alter_column(
        "password_resets",
        "expires_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(timezone=False),
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
    )
