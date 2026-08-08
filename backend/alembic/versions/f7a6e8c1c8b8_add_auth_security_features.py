"""add_auth_security_features

Revision ID: f7a6e8c1c8b8
Revises: add_refunded_amount
Create Date: 2025-12-27 23:39:36.450510

Migration Description:
    Add authentication security features:
    - Add user verification fields
    - Add login attempt tracking fields
    - Various index improvements

"""
import os
import sys
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Add backend directory to path for migration_helpers import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from migration_helpers import (
    safe_add_column, safe_drop_column,
    safe_create_index, safe_drop_index,
    safe_drop_constraint, safe_create_unique_constraint,
    table_exists, column_exists, index_exists, constraint_exists
)

# revision identifiers, used by Alembic.
revision: str = 'f7a6e8c1c8b8'
down_revision: Union[str, None] = 'add_refunded_amount'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply authentication security features migration."""
    
    # Create notification index if not exists
    safe_create_index('ix_notifications_user_read_created', 'notifications', ['user_id', 'is_read', 'created_at'])
    
    # Update project_members joined_at timezone
    op.alter_column('project_members', 'joined_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    
    # Create unique constraint on project_members (safe - won't fail if already exists)
    safe_create_unique_constraint('uq_project_members_project_user', 'project_members', ['project_id', 'user_id'])
    
    # Drop old unique constraint on subscriptions (safe - won't fail if not exists)
    safe_drop_constraint('subscriptions_user_id_key', 'subscriptions', type_='unique')
    
    # Create task index
    safe_create_index('ix_tasks_project_due_date', 'tasks', ['project_id', 'due_date'])
    
    # Add user verification columns
    safe_add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=True))
    safe_add_column('users', sa.Column('verification_token', sa.String(length=255), nullable=True))
    safe_add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=True))
    safe_add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    
    # Update github_id index (safe - use helper functions)
    safe_drop_constraint('users_github_id_key', 'users', type_='unique')
    safe_create_index('ix_users_github_id', 'users', ['github_id'], unique=True)
    
    # Drop unused TOTP columns if they exist
    safe_drop_column('users', 'backup_codes')
    safe_drop_column('users', 'totp_enabled')
    safe_drop_column('users', 'totp_secret')


def downgrade() -> None:
    """Revert authentication security features migration."""
    # Restore TOTP columns
    safe_add_column('users', sa.Column('totp_secret', sa.VARCHAR(length=255), nullable=True))
    safe_add_column('users', sa.Column('totp_enabled', sa.BOOLEAN(), server_default=sa.text('false'), nullable=True))
    safe_add_column('users', sa.Column('backup_codes', sa.TEXT(), nullable=True))
    
    # Restore github_id constraint
    safe_drop_index('ix_users_github_id', 'users')
    safe_create_unique_constraint('users_github_id_key', 'users', ['github_id'])
    
    # Remove user verification columns
    safe_drop_column('users', 'locked_until')
    safe_drop_column('users', 'failed_login_attempts')
    safe_drop_column('users', 'verification_token')
    safe_drop_column('users', 'is_verified')
    
    # Drop task index
    safe_drop_index('ix_tasks_project_due_date', 'tasks')
    
    # Restore subscriptions constraint
    safe_create_unique_constraint('subscriptions_user_id_key', 'subscriptions', ['user_id'])
    
    # Drop project_members constraint
    safe_drop_constraint('uq_project_members_project_user', 'project_members', type_='unique')
    
    # Revert project_members joined_at timezone
    op.alter_column('project_members', 'joined_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    
    # Drop notification index
    safe_drop_index('ix_notifications_user_read_created', 'notifications')

