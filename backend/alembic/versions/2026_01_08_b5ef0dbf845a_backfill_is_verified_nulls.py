"""backfill_is_verified_nulls

Revision ID: b5ef0dbf845a
Revises: b82e1628d697
Create Date: 2026-01-08 05:02:54.778766+00:00

Migration Description:
    Backfill is_verified to TRUE for all existing users.
    Previous migration set existing users to FALSE, locking them out.

WARNING: Always test migrations in a development environment before production!
"""
import os
import sys
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Add backend directory to path for migration_helpers import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from migration_helpers import (
    safe_add_column, safe_drop_column,
    safe_create_index, safe_drop_index,
    safe_create_table, safe_drop_table,
    safe_create_foreign_key, safe_drop_constraint,
    column_exists, table_exists, index_exists
)

# revision identifiers, used by Alembic.
revision: str = 'b5ef0dbf845a'
down_revision: Union[str, None] = 'b82e1628d697'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply the migration changes.
    """
    # Fix existing users who were set to is_verified=False
    # This assumes that all users who were in the system before verification
    # was introduced should be treated as verified.
    op.execute("UPDATE users SET is_verified = TRUE")


def downgrade() -> None:
    """
    Revert the migration changes.
    """
    # We cannot know which users were previously FALSE vs TRUE,
    # so we do not revert this data change to avoid locking out legitimate users.
    pass
