"""create_security_logs_table

Revision ID: security_logs_001
Revises: h9c8g0d2e2b0
Create Date: 2026-01-03 16:30:00.000000

Migration Description:
    Create security_logs table for tracking security events such as
    failed login attempts, suspicious activity, and access violations.
    Used for security auditing and monitoring.

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
revision: str = 'security_logs_001'
down_revision: str | Sequence[str] | None = 'h9c8g0d2e2b0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create security_logs table for security event tracking."""
    if not table_exists('security_logs'):
        op.create_table(
            'security_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
            sa.Column('event_type', sa.String(length=50), nullable=False),
            sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('severity', sa.String(length=20), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.String(length=255), nullable=True),
            sa.Column('request_path', sa.String(length=255), nullable=True),
            sa.Column('request_method', sa.String(length=10), nullable=True),
            sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )

    # Create indexes (safe - won't fail if already exists)
    safe_create_index('ix_security_logs_event_type', 'security_logs', ['event_type'])
    safe_create_index('ix_security_logs_timestamp', 'security_logs', ['timestamp'])
    safe_create_index('ix_security_logs_user_id', 'security_logs', ['user_id'])


def downgrade() -> None:
    """Drop security_logs table and its indexes."""
    safe_drop_index('ix_security_logs_user_id', 'security_logs')
    safe_drop_index('ix_security_logs_timestamp', 'security_logs')
    safe_drop_index('ix_security_logs_event_type', 'security_logs')
    safe_drop_table('security_logs')
