"""Add Stripe terminal incomplete status and remove redundant invoice index.

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-08-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "j3k4l5m6n7o8"
down_revision: str | Sequence[str] | None = "i2j3k4l5m6n7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep the model enum in sync with Stripe and remove duplicate storage."""
    op.execute(
        "ALTER TYPE subscriptionstatus "
        "ADD VALUE IF NOT EXISTS 'incomplete_expired'"
    )
    op.execute("DROP INDEX IF EXISTS ix_payment_history_stripe_invoice_id")


def downgrade() -> None:
    """The enum value is intentionally not removed; PostgreSQL cannot safely
    remove enum labels in-place. Recreate the redundant index only."""
    op.create_index(
        "ix_payment_history_stripe_invoice_id",
        "payment_history",
        ["stripe_invoice_id"],
        unique=False,
    )
