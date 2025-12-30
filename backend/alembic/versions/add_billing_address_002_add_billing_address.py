"""Add billing address fields to payment_methods

Revision ID: add_billing_address_002
Revises: add_payment_tables_001
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_billing_address_002'
down_revision: Union[str, None] = 'add_payment_tables_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add billing address columns to payment_methods
    op.add_column('payment_methods', sa.Column('billing_phone', sa.String(50), nullable=True))
    op.add_column('payment_methods', sa.Column('billing_address_line1', sa.String(255), nullable=True))
    op.add_column('payment_methods', sa.Column('billing_address_line2', sa.String(255), nullable=True))
    op.add_column('payment_methods', sa.Column('billing_city', sa.String(100), nullable=True))
    op.add_column('payment_methods', sa.Column('billing_state', sa.String(100), nullable=True))
    op.add_column('payment_methods', sa.Column('billing_postal_code', sa.String(20), nullable=True))
    op.add_column('payment_methods', sa.Column('billing_country', sa.String(2), nullable=True))  # ISO 3166-1 alpha-2
    
    # Add additional card info from Stripe
    op.add_column('payment_methods', sa.Column('card_country', sa.String(2), nullable=True))  # Card issuer country
    op.add_column('payment_methods', sa.Column('card_fingerprint', sa.String(255), nullable=True))  # For duplicate detection
    
    # Create index on card_fingerprint for duplicate detection
    op.create_index('ix_payment_methods_card_fingerprint', 'payment_methods', ['card_fingerprint'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_payment_methods_card_fingerprint', 'payment_methods')
    
    # Drop columns
    op.drop_column('payment_methods', 'card_fingerprint')
    op.drop_column('payment_methods', 'card_country')
    op.drop_column('payment_methods', 'billing_country')
    op.drop_column('payment_methods', 'billing_postal_code')
    op.drop_column('payment_methods', 'billing_state')
    op.drop_column('payment_methods', 'billing_city')
    op.drop_column('payment_methods', 'billing_address_line2')
    op.drop_column('payment_methods', 'billing_address_line1')
    op.drop_column('payment_methods', 'billing_phone')
