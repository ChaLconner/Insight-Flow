"""Add billing address fields to payment_methods

Revision ID: add_billing_address_002
Revises: add_payment_tables_001
Create Date: 2025-12-25

Migration Description:
    Add billing address columns to payment_methods table for complete
    payment information. Also adds card country and fingerprint for
    fraud detection and duplicate card prevention.

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

from migration_helpers import (
    safe_add_column, safe_drop_column,
    safe_create_index, safe_drop_index
)

# revision identifiers, used by Alembic.
revision: str = 'add_billing_address_002'
down_revision: str | Sequence[str] | None = 'add_payment_tables_001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add billing address and card info columns to payment_methods."""
    # Add billing address columns to payment_methods
    safe_add_column('payment_methods', sa.Column('billing_phone', sa.String(50), nullable=True))
    safe_add_column('payment_methods', sa.Column('billing_address_line1', sa.String(255), nullable=True))
    safe_add_column('payment_methods', sa.Column('billing_address_line2', sa.String(255), nullable=True))
    safe_add_column('payment_methods', sa.Column('billing_city', sa.String(100), nullable=True))
    safe_add_column('payment_methods', sa.Column('billing_state', sa.String(100), nullable=True))
    safe_add_column('payment_methods', sa.Column('billing_postal_code', sa.String(20), nullable=True))
    # ISO 3166-1 alpha-2 country code
    safe_add_column('payment_methods', sa.Column('billing_country', sa.String(2), nullable=True))

    # Add additional card info from Stripe
    safe_add_column('payment_methods', sa.Column('card_country', sa.String(2), nullable=True))
    # Card fingerprint for duplicate detection
    safe_add_column('payment_methods', sa.Column('card_fingerprint', sa.String(255), nullable=True))

    # Create index on card_fingerprint for duplicate detection
    safe_create_index('ix_payment_methods_card_fingerprint', 'payment_methods', ['card_fingerprint'])


def downgrade() -> None:
    """Remove billing address and card info columns from payment_methods."""
    # Drop index
    safe_drop_index('ix_payment_methods_card_fingerprint', 'payment_methods')

    # Drop columns
    safe_drop_column('payment_methods', 'card_fingerprint')
    safe_drop_column('payment_methods', 'card_country')
    safe_drop_column('payment_methods', 'billing_country')
    safe_drop_column('payment_methods', 'billing_postal_code')
    safe_drop_column('payment_methods', 'billing_state')
    safe_drop_column('payment_methods', 'billing_city')
    safe_drop_column('payment_methods', 'billing_address_line2')
    safe_drop_column('payment_methods', 'billing_address_line1')
    safe_drop_column('payment_methods', 'billing_phone')
