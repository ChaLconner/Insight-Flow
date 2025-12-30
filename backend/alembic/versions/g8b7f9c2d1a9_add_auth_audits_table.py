"""add_auth_audits_table

Revision ID: g8b7f9c2d1a9
Revises: f7a6e8c1c8b8
Create Date: 2025-12-28 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g8b7f9c2d1a9'
down_revision: Union[str, None] = 'f7a6e8c1c8b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create auth_audits table for tracking login attempts
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
    # Create indexes for common queries
    op.create_index('ix_auth_audits_user_id', 'auth_audits', ['user_id'], unique=False)
    op.create_index('ix_auth_audits_email', 'auth_audits', ['email'], unique=False)
    op.create_index('ix_auth_audits_attempt_at', 'auth_audits', ['attempt_at'], unique=False)
    op.create_index('ix_auth_audits_status', 'auth_audits', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_auth_audits_status', table_name='auth_audits')
    op.drop_index('ix_auth_audits_attempt_at', table_name='auth_audits')
    op.drop_index('ix_auth_audits_email', table_name='auth_audits')
    op.drop_index('ix_auth_audits_user_id', table_name='auth_audits')
    op.drop_table('auth_audits')
