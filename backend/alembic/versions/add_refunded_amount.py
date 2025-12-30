"""add refunded_amount to payment_history

Revision ID: add_refunded_amount
Revises: 
Create Date: 2025-12-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_refunded_amount'
down_revision: Union[str, None] = 'add_webhook_event_log'  # Previous migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add refunded_amount column to payment_history table."""
    op.add_column(
        'payment_history',
        sa.Column('refunded_amount', sa.Numeric(10, 2), nullable=True)
    )


def downgrade() -> None:
    """Remove refunded_amount column from payment_history table."""
    op.drop_column('payment_history', 'refunded_amount')
