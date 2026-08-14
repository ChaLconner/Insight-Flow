"""add refunded_amount to payment_history

Revision ID: add_refunded_amount
Revises: add_webhook_event_log
Create Date: 2025-12-27

Migration Description:
    Add refunded_amount column to payment_history table for tracking
    partial refunds on payments.

"""
import os
import sys
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# Add backend directory to path for migration_helpers import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from migration_helpers import safe_add_column, safe_drop_column

# revision identifiers, used by Alembic.
revision: str = 'add_refunded_amount'
down_revision: str | Sequence[str] | None = 'add_webhook_event_log'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add refunded_amount column to payment_history table."""
    safe_add_column(
        'payment_history',
        sa.Column('refunded_amount', sa.Numeric(10, 2), nullable=True)
    )


def downgrade() -> None:
    """Remove refunded_amount column from payment_history table."""
    safe_drop_column('payment_history', 'refunded_amount')
