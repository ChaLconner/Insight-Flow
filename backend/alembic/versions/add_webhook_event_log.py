"""Add webhook event log table

Revision ID: add_webhook_event_log
Revises: 
Create Date: 2025-12-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_webhook_event_log'
down_revision = '1fd46ce005d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'webhook_event_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stripe_event_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('processed', sa.Boolean(), nullable=False, default=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('raw_payload', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for efficient duplicate checking
    op.create_index('ix_webhook_event_logs_stripe_event_id', 'webhook_event_logs', ['stripe_event_id'], unique=True)
    op.create_index('ix_webhook_event_logs_event_type', 'webhook_event_logs', ['event_type'])
    op.create_index('ix_webhook_event_logs_user_id', 'webhook_event_logs', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_webhook_event_logs_user_id', table_name='webhook_event_logs')
    op.drop_index('ix_webhook_event_logs_event_type', table_name='webhook_event_logs')
    op.drop_index('ix_webhook_event_logs_stripe_event_id', table_name='webhook_event_logs')
    op.drop_table('webhook_event_logs')
