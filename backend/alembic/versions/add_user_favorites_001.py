"""add user_favorites table

Revision ID: add_user_favorites_001
Revises: g8b7f9c2d1a9
Create Date: 2025-12-28 15:20:00.000000

Migration Description:
    Create user_favorites table for allowing users to mark projects
    as favorites. Includes unique constraint on user-project pairs
    and indexes for efficient queries.

"""
import os
import sys

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
revision = 'add_user_favorites_001'
down_revision = 'g8b7f9c2d1a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create user_favorites table for project bookmarking."""
    # Create user_favorites table only if not exists
    if not table_exists('user_favorites'):
        op.create_table(
            'user_favorites',
            sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', sa.UUID(as_uuid=True), nullable=False),
            sa.Column('project_id', sa.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'project_id', name='uq_user_favorites_user_project')
        )

    # Create indexes (safe - won't fail if already exists)
    safe_create_index('ix_user_favorites_user_id', 'user_favorites', ['user_id'])
    safe_create_index('ix_user_favorites_project_id', 'user_favorites', ['project_id'])
    safe_create_index('ix_user_favorites_user_project', 'user_favorites', ['user_id', 'project_id'])


def downgrade() -> None:
    """Drop user_favorites table and its indexes."""
    # Drop indexes
    safe_drop_index('ix_user_favorites_user_project', 'user_favorites')
    safe_drop_index('ix_user_favorites_project_id', 'user_favorites')
    safe_drop_index('ix_user_favorites_user_id', 'user_favorites')

    # Drop table
    safe_drop_table('user_favorites')
