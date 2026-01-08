"""add_verification_token_expiration

Revision ID: v_token_expiry_001
Revises: security_logs_001
Create Date: 2026-01-05 17:37:00.000000

Migration Description:
    Add verification_token_expires_at column to users table for
    email verification token expiration tracking.

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

from migration_helpers import safe_add_column, safe_drop_column

# revision identifiers, used by Alembic.
revision: str = 'v_token_expiry_001'
down_revision: Union[str, None] = 'security_logs_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add verification_token_expires_at column to users table."""
    safe_add_column(
        'users',
        sa.Column('verification_token_expires_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove verification_token_expires_at column from users table."""
    safe_drop_column('users', 'verification_token_expires_at')
