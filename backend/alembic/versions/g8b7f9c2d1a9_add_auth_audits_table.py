"""add_auth_audits_table

Revision ID: g8b7f9c2d1a9
Revises: f7a6e8c1c8b8
Create Date: 2025-12-28 14:05:00.000000

Migration Description:
    Create auth_audits table for tracking login attempts and authentication
    events. Includes indexes for efficient querying by user, email, time,
    and status.

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
    safe_create_table, safe_drop_table,
    safe_create_index, safe_drop_index,
    table_exists
)

# revision identifiers, used by Alembic.
revision: str = 'g8b7f9c2d1a9'
down_revision: Union[str, None] = 'f7a6e8c1c8b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create auth_audits table for tracking login attempts."""
    # Create auth_audits table only if not exists
    if not table_exists('auth_audits'):
        op.create_table('auth_audits',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=True),
            sa.Column('email', sa.String(length=255), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.String(length=255), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False),
            sa.Column('attempt_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # Create indexes for common queries (safe - won't fail if already exists)
    safe_create_index('ix_auth_audits_user_id', 'auth_audits', ['user_id'])
    safe_create_index('ix_auth_audits_email', 'auth_audits', ['email'])
    safe_create_index('ix_auth_audits_attempt_at', 'auth_audits', ['attempt_at'])
    safe_create_index('ix_auth_audits_status', 'auth_audits', ['status'])


def downgrade() -> None:
    """Drop auth_audits table and its indexes."""
    safe_drop_index('ix_auth_audits_status', 'auth_audits')
    safe_drop_index('ix_auth_audits_attempt_at', 'auth_audits')
    safe_drop_index('ix_auth_audits_email', 'auth_audits')
    safe_drop_index('ix_auth_audits_user_id', 'auth_audits')
    safe_drop_table('auth_audits')
