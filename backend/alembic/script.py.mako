"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

Migration Description:
    TODO: Add a detailed description of what this migration does.

WARNING: Always test migrations in a development environment before production!
"""
import os
import sys
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

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
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """
    Apply the migration changes.
    
    Use safe_* functions from migration_helpers to prevent errors:
    - safe_add_column(table, column) - Add column if not exists
    - safe_drop_column(table, column_name) - Drop column if exists
    - safe_create_index(name, table, columns) - Create index if not exists
    - safe_drop_index(name, table) - Drop index if exists
    - safe_create_table(name, *columns) - Create table if not exists
    - safe_drop_table(name) - Drop table if exists
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """
    Revert the migration changes.
    
    Note: Data loss may occur when reverting certain operations.
    Always backup data before running downgrade in production.
    """
    ${downgrades if downgrades else "pass"}
