"""
Webhook Event Log model for tracking Stripe webhook events.
Provides idempotency and audit trail for all incoming webhooks.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class WebhookEventLog(BaseModel):
    """
    Log of all incoming Stripe webhook events for idempotency and debugging.
    """

    __tablename__ = "webhook_event_logs"

    # Stripe event ID (unique from Stripe)
    stripe_event_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # Event type (e.g., "customer.subscription.updated")
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Processing status
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Raw payload (for debugging)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    # Associated user (if determinable)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
