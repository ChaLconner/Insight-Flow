"""create_security_logs_table

Revision ID: security_logs_001
Revises: g8b7f9c2d1a9
Create Date: 2026-01-03 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'security_logs_001'
down_revision: Union[str, Sequence[str], None] = 'h9c8g0d2e2b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    
    op.create_index(op.f('ix_security_logs_event_type'), 'security_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_security_logs_timestamp'), 'security_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_security_logs_user_id'), 'security_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_security_logs_user_id'), table_name='security_logs')
    op.drop_index(op.f('ix_security_logs_timestamp'), table_name='security_logs')
    op.drop_index(op.f('ix_security_logs_event_type'), table_name='security_logs')
    op.drop_table('security_logs')
