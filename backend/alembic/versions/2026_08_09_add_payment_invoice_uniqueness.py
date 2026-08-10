"""Enforce one payment history row per Stripe invoice.

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6
Create Date: 2026-08-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "i2j3k4l5m6n7"
down_revision: str | Sequence[str] | None = "h1i2j3k4l5m6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Reject duplicate invoice facts before adding the uniqueness invariant."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT stripe_invoice_id
                FROM payment_history
                WHERE stripe_invoice_id IS NOT NULL
                GROUP BY stripe_invoice_id
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot add invoice uniqueness: duplicate Stripe invoices exist';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_payment_history_stripe_invoice_id'
                  AND conrelid = 'public.payment_history'::regclass
            ) THEN
                ALTER TABLE payment_history
                    ADD CONSTRAINT uq_payment_history_stripe_invoice_id
                    UNIQUE (stripe_invoice_id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE payment_history "
        "DROP CONSTRAINT IF EXISTS uq_payment_history_stripe_invoice_id"
    )
