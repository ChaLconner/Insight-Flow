"""Add webhook event log table

Revision ID: add_webhook_event_log
Revises: 1fd46ce005d8
Create Date: 2025-12-26

Migration Description:
    Create webhook_event_logs table for tracking Stripe webhook events
    and preventing duplicate event processing.

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
    safe_create_index, safe_drop_index,
    safe_create_table, safe_drop_table,
    table_exists
)

# revision identifiers, used by Alembic.
revision = 'add_webhook_event_log'
down_revision = '1fd46ce005d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create webhook_event_logs table for Stripe event deduplication."""
    
    # Only create if table doesn't exist
    if not table_exists('webhook_event_logs'):
        op.create_table(
            'webhook_event_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('stripe_event_id', sa.String(255), nullable=False),
            sa.Column('event_type', sa.String(100), nullable=False),
            sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('raw_payload', sa.Text(), nullable=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

    # Create indexes (safe - won't fail if already exists)
    safe_create_index('ix_webhook_event_logs_stripe_event_id', 'webhook_event_logs', ['stripe_event_id'], unique=True)
    safe_create_index('ix_webhook_event_logs_event_type', 'webhook_event_logs', ['event_type'])
    safe_create_index('ix_webhook_event_logs_user_id', 'webhook_event_logs', ['user_id'])


def downgrade() -> None:
    """Drop webhook_event_logs table."""
    safe_drop_index('ix_webhook_event_logs_user_id', 'webhook_event_logs')
    safe_drop_index('ix_webhook_event_logs_event_type', 'webhook_event_logs')
    safe_drop_index('ix_webhook_event_logs_stripe_event_id', 'webhook_event_logs')
    safe_drop_table('webhook_event_logs')
