"""merge heads

Revision ID: 1fd46ce005d8
Revises: add_billing_address_002, add_stripe_customer_id
Create Date: 2025-12-26 16:20:54.823332

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fd46ce005d8'
down_revision: str | Sequence[str] | None = ('add_billing_address_002', 'add_stripe_customer_id')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # This merge revision only joins existing heads; it introduces no schema changes.
    pass


def downgrade() -> None:
    # This merge revision only joins existing heads; it introduces no schema changes to reverse.
    pass
