"""add_auth_security_features

Revision ID: f7a6e8c1c8b8
Revises: add_refunded_amount
Create Date: 2025-12-27 23:39:36.450510

Migration Description:
    Add authentication security features:
    - Create webhook_event_logs table (if not exists)
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
    safe_create_table, safe_drop_table,
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
    
    # Create webhook_event_logs table only if it doesn't exist
    # (May have been created by add_webhook_event_log migration)
    if not table_exists('webhook_event_logs'):
        op.create_table('webhook_event_logs',
            sa.Column('stripe_event_id', sa.String(length=255), nullable=False),
            sa.Column('event_type', sa.String(length=100), nullable=False),
            sa.Column('processed', sa.Boolean(), nullable=False),
            sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('retry_count', sa.Integer(), nullable=False),
            sa.Column('raw_payload', sa.Text(), nullable=True),
            sa.Column('user_id', sa.UUID(), nullable=True),
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        safe_create_index('ix_webhook_event_logs_event_type', 'webhook_event_logs', ['event_type'])
        safe_create_index('ix_webhook_event_logs_stripe_event_id', 'webhook_event_logs', ['stripe_event_id'], unique=True)
        safe_create_index('ix_webhook_event_logs_user_id', 'webhook_event_logs', ['user_id'])
    
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
    
    # Drop webhook_event_logs table and indexes
    safe_drop_index('ix_webhook_event_logs_user_id', 'webhook_event_logs')
    safe_drop_index('ix_webhook_event_logs_stripe_event_id', 'webhook_event_logs')
    safe_drop_index('ix_webhook_event_logs_event_type', 'webhook_event_logs')
    safe_drop_table('webhook_event_logs')

