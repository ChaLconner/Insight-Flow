"""Add payment tables

Revision ID: add_payment_tables_001
Revises: add_github_id_001
Create Date: 2025-12-25

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

_NOW_SQL = "now()"
_USERS_ID = "users.id"
_SET_NULL = "SET NULL"

# revision identifiers, used by Alembic.
revision: str = 'add_payment_tables_001'
down_revision: str | Sequence[str] | None = 'add_github_id_001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create subscription_status enum
    subscription_status = postgresql.ENUM(
        'active', 'canceled', 'past_due', 'trialing', 'unpaid', 'incomplete',
        name='subscriptionstatus',
        create_type=False
    )
    subscription_status.create(op.get_bind(), checkfirst=True)

    # Create subscription_plan enum
    subscription_plan = postgresql.ENUM(
        'free', 'starter', 'pro', 'enterprise',
        name='subscriptionplan',
        create_type=False
    )
    subscription_plan.create(op.get_bind(), checkfirst=True)

    # Create payment_status enum
    payment_status = postgresql.ENUM(
        'pending', 'succeeded', 'failed', 'refunded', 'canceled',
        name='paymentstatus',
        create_type=False
    )
    payment_status.create(op.get_bind(), checkfirst=True)

    # Create payment_methods table
    op.create_table(
        'payment_methods',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(_NOW_SQL), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text(_NOW_SQL), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('stripe_payment_method_id', sa.String(255), nullable=False),
        sa.Column('stripe_customer_id', sa.String(255), nullable=False),
        sa.Column('card_brand', sa.String(50), nullable=False),
        sa.Column('card_last4', sa.String(4), nullable=False),
        sa.Column('card_exp_month', sa.Integer(), nullable=False),
        sa.Column('card_exp_year', sa.Integer(), nullable=False),
        sa.Column('card_funding', sa.String(20), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('billing_name', sa.String(255), nullable=True),
        sa.Column('billing_email', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], [_USERS_ID], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payment_methods_user_id', 'payment_methods', ['user_id'])
    op.create_index('ix_payment_methods_stripe_payment_method_id', 'payment_methods', ['stripe_payment_method_id'], unique=True)
    op.create_index('ix_payment_methods_stripe_customer_id', 'payment_methods', ['stripe_customer_id'])

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(_NOW_SQL), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text(_NOW_SQL), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('plan', postgresql.ENUM('free', 'starter', 'pro', 'enterprise', name='subscriptionplan', create_type=False), nullable=False, default='free'),
        sa.Column('status', postgresql.ENUM('active', 'canceled', 'past_due', 'trialing', 'unpaid', 'incomplete', name='subscriptionstatus', create_type=False), nullable=False, default='active'),
        sa.Column('current_period_start', sa.String(50), nullable=True),
        sa.Column('current_period_end', sa.String(50), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, default=False),
        sa.Column('default_payment_method_id', sa.UUID(), nullable=True),
        sa.Column('price_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('price_currency', sa.String(3), default='usd', nullable=True),
        sa.ForeignKeyConstraint(['user_id'], [_USERS_ID], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['default_payment_method_id'], ['payment_methods.id'], ondelete=_SET_NULL),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'], unique=True)
    op.create_index('ix_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'], unique=True)
    op.create_index('ix_subscriptions_stripe_customer_id', 'subscriptions', ['stripe_customer_id'])

    # Create payment_history table
    op.create_table(
        'payment_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(_NOW_SQL), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text(_NOW_SQL), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('subscription_id', sa.UUID(), nullable=True),
        sa.Column('payment_method_id', sa.UUID(), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(255), nullable=True),
        sa.Column('stripe_invoice_id', sa.String(255), nullable=True),
        sa.Column('stripe_charge_id', sa.String(255), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='usd'),
        sa.Column('status', postgresql.ENUM('pending', 'succeeded', 'failed', 'refunded', 'canceled', name='paymentstatus', create_type=False), nullable=False, default='pending'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('invoice_url', sa.String(500), nullable=True),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('failure_code', sa.String(100), nullable=True),
        sa.Column('failure_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], [_USERS_ID], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete=_SET_NULL),
        sa.ForeignKeyConstraint(['payment_method_id'], ['payment_methods.id'], ondelete=_SET_NULL),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payment_history_user_id', 'payment_history', ['user_id'])
    op.create_index('ix_payment_history_stripe_payment_intent_id', 'payment_history', ['stripe_payment_intent_id'], unique=True)
    op.create_index('ix_payment_history_stripe_invoice_id', 'payment_history', ['stripe_invoice_id'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('payment_history')
    op.drop_table('subscriptions')
    op.drop_table('payment_methods')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS paymentstatus')
    op.execute('DROP TYPE IF EXISTS subscriptionplan')
    op.execute('DROP TYPE IF EXISTS subscriptionstatus')
