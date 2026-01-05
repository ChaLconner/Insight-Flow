"""add stripe_customer_id to users table

Revision ID: add_stripe_customer_id
Revises: 
Create Date: 2025-12-26 13:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_stripe_customer_id'
down_revision = 'add_payment_tables_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add stripe_customer_id column to users table for caching Stripe customer ID."""
    # Try to add the column, skip if it already exists
    try:
        op.add_column('users', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
        op.create_index('ix_users_stripe_customer_id', 'users', ['stripe_customer_id'], unique=False)
    except Exception:
        pass  # Column may already exist


def downgrade() -> None:
    """Remove stripe_customer_id column from users table."""
    try:
        op.drop_index('ix_users_stripe_customer_id', table_name='users')
        op.drop_column('users', 'stripe_customer_id')
    except Exception:
        pass
