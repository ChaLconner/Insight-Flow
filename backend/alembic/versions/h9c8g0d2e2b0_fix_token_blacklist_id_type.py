"""fix_token_blacklist_id_type - Change id from INTEGER to UUID

Revision ID: h9c8g0d2e2b0
Revises: 9cd1cf9585b5
Create Date: 2025-12-31 17:34:00.000000

Migration Description:
    Fix token_blacklist table by changing id column from INTEGER to UUID.
    Drops and recreates the table since token blacklist data is transient
    and can be safely regenerated.

"""
import os
import sys
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Add backend directory to path for migration_helpers import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from migration_helpers import (
    safe_create_table, safe_drop_table,
    safe_create_index, safe_drop_index,
    table_exists
)

# revision identifiers, used by Alembic.
revision: str = 'h9c8g0d2e2b0'
down_revision: str | Sequence[str] | None = '9cd1cf9585b5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Recreate token_blacklist table with correct UUID type for id column."""
    # Drop the old table if it exists (token blacklist data can be regenerated)
    safe_drop_table('token_blacklist')

    # Create the table with correct UUID type
    op.create_table('token_blacklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_jti', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    safe_create_index('ix_token_blacklist_token_jti', 'token_blacklist', ['token_jti'], unique=True)


def downgrade() -> None:
    """Drop token_blacklist table."""
    safe_drop_index('ix_token_blacklist_token_jti', 'token_blacklist')
    safe_drop_table('token_blacklist')
