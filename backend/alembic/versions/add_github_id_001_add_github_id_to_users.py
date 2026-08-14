"""Add github_id to users

Revision ID: add_github_id_001
Revises: 58e012fdb79c
Create Date: 2025-12-15

Migration Description:
    Add github_id column to users table for GitHub OAuth integration.
    Includes unique index for fast lookups and duplicate prevention.

"""
import os
import sys
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# Add backend directory to path for migration_helpers import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from migration_helpers import (
    safe_add_column, safe_drop_column,
    safe_create_index, safe_drop_index
)

# revision identifiers, used by Alembic.
revision: str = 'add_github_id_001'
down_revision: str | Sequence[str] | None = '58e012fdb79c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add github_id column to users table for GitHub OAuth support."""
    # Add github_id column to users table
    safe_add_column('users', sa.Column('github_id', sa.String(255), nullable=True))
    # Create unique index on github_id
    safe_create_index('ix_users_github_id', 'users', ['github_id'], unique=True)


def downgrade() -> None:
    """Remove github_id column and index from users table."""
    # Remove index and column
    safe_drop_index('ix_users_github_id', 'users')
    safe_drop_column('users', 'github_id')
