"""
Payment-related models for Insight-Flow application.
Supports Stripe integration for payment method management and subscriptions.
"""

import enum
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .user import User


class SubscriptionStatus(enum.StrEnum):
    """Subscription status enum."""

    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"


class SubscriptionPlan(enum.StrEnum):
    """Available subscription plans."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class PaymentStatus(enum.StrEnum):
    """Payment transaction status."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"


class PaymentMethod(BaseModel):
    """
    Payment method model for storing linked cards.
    Stores only Stripe tokens and masked card info for PCI compliance.
    """

    __tablename__ = "payment_methods"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stripe_payment_method_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Card details (safe to store - masked/non-sensitive)
    card_brand: Mapped[str] = mapped_column(String(50), nullable=False)
    card_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    card_exp_month: Mapped[int] = mapped_column(Integer, nullable=False)
    card_exp_year: Mapped[int] = mapped_column(Integer, nullable=False)
    card_funding: Mapped[str | None] = mapped_column(String(20), nullable=True)
    card_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    card_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Status
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Billing contact info
    billing_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billing_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Billing address
    billing_address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billing_address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billing_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    billing_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    billing_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    billing_country: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="payment_methods")
    transactions: Mapped[list["PaymentHistory"]] = relationship(
        "PaymentHistory", back_populates="payment_method"
    )


class Subscription(BaseModel):
    """
    Subscription model for tracking user subscriptions.
    """

    __tablename__ = "subscriptions"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Plan details
    plan: Mapped[SubscriptionPlan] = mapped_column(
        SQLEnum(SubscriptionPlan, values_callable=lambda x: [e.value for e in x]),
        default=SubscriptionPlan.FREE,
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus, values_callable=lambda x: [e.value for e in x]),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )

    # Billing cycle
    current_period_start: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_period_end: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Payment method reference
    default_payment_method_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_methods.id", ondelete="SET NULL"), nullable=True
    )

    # Pricing
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_currency: Mapped[str | None] = mapped_column(String(3), default="usd", nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="subscription")
    default_payment_method: Mapped[Optional["PaymentMethod"]] = relationship("PaymentMethod")
    payments: Mapped[list["PaymentHistory"]] = relationship(
        "PaymentHistory", back_populates="subscription"
    )

    __table_args__ = (
        Index("ix_subscriptions_default_payment_method_id", "default_payment_method_id"),
    )


class PaymentHistory(BaseModel):
    """
    Payment history model for tracking all transactions.
    """

    __tablename__ = "payment_history"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    payment_method_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_methods.id", ondelete="SET NULL"), nullable=True
    )

    # Stripe references
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_charge_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Transaction details
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, values_callable=lambda x: [e.value for e in x]),
        default=PaymentStatus.PENDING,
        nullable=False,
    )

    # Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Error handling
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Refund tracking
    refunded_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, default=None
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="payment_history")
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription", back_populates="payments"
    )
    payment_method: Mapped[Optional["PaymentMethod"]] = relationship(
        "PaymentMethod", back_populates="transactions"
    )

    __table_args__ = (
        Index("ix_payment_history_user_created_at", "user_id", "created_at"),
        Index("ix_payment_history_subscription_id", "subscription_id"),
        Index("ix_payment_history_payment_method_id", "payment_method_id"),
    )
