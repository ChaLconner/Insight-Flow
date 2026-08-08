"""add user first_name and last_name fields

Revision ID: c8d9e0f1a2b3
Revises: b982c771a39f
Create Date: 2026-08-07 18:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from migration_helpers import safe_add_column

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: str | None = "b982c771a39f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add columns idempotently because CI seeds the legacy model schema first.
    safe_add_column("users", sa.Column("first_name", sa.String(length=255), nullable=True))
    safe_add_column("users", sa.Column("last_name", sa.String(length=255), nullable=True))
    op.alter_column("users", "name", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("last_name")
        batch_op.drop_column("first_name")
        batch_op.alter_column("name", nullable=False)
