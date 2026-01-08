"""add stripe_customer_id to users table

Revision ID: add_stripe_customer_id
Revises: add_payment_tables_001
Create Date: 2025-12-26 13:45:00.000000

"""
import os
import sys

# Add backend directory to path for migration_helpers import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from alembic import op
import sqlalchemy as sa

from migration_helpers import (
    safe_add_column, safe_drop_column,
    safe_create_index, safe_drop_index
)


# revision identifiers, used by Alembic.
revision = 'add_stripe_customer_id'
down_revision = 'add_payment_tables_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add stripe_customer_id column to users table for caching Stripe customer ID."""
    safe_add_column(
        'users',
        sa.Column('stripe_customer_id', sa.String(255), nullable=True)
    )
    safe_create_index(
        'ix_users_stripe_customer_id',
        'users',
        ['stripe_customer_id'],
        unique=False
    )


def downgrade() -> None:
    """Remove stripe_customer_id column from users table."""
    safe_drop_index('ix_users_stripe_customer_id', 'users')
    safe_drop_column('users', 'stripe_customer_id')
