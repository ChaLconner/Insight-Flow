"""
Payment-related Pydantic schemas for Insight-Flow application.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ============================================================================
# Enums (mirror database enums)
# ============================================================================


class SubscriptionStatusEnum(str, Enum):
    """Subscription status enum."""

    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"


class SubscriptionPlanEnum(str, Enum):
    """Available subscription plans."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class PaymentStatusEnum(str, Enum):
    """Payment transaction status."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"


# ============================================================================
# Payment Method Schemas
# ============================================================================


class BillingAddress(BaseModel):
    """Billing address schema."""

    line1: str | None = Field(None, max_length=255)
    line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=2, description="ISO 3166-1 alpha-2 country code")


class PaymentMethodCreate(BaseModel):
    """Schema for creating a new payment method via Stripe SetupIntent."""

    payment_method_id: str = Field(..., description="Stripe payment_method_id from frontend")
    customer_id: str = Field(..., description="Stripe customer_id")
    set_as_default: bool = Field(
        default=True, description="Whether to set as default payment method"
    )

    # Billing contact info
    billing_name: str | None = Field(None, max_length=255)
    billing_email: EmailStr | None = None
    billing_phone: str | None = Field(None, max_length=50)

    # Billing address
    billing_address: BillingAddress | None = None


class PaymentMethodResponse(BaseModel):
    """Response schema for payment method (safe - no sensitive data)."""

    id: UUID
    card_brand: str
    card_last4: str
    card_exp_month: int
    card_exp_year: int
    card_funding: str | None = None
    card_country: str | None = None
    is_default: bool
    is_active: bool

    # Billing contact info
    billing_name: str | None = None
    billing_email: str | None = None
    billing_phone: str | None = None

    # Billing address
    billing_address_line1: str | None = None
    billing_address_line2: str | None = None
    billing_city: str | None = None
    billing_state: str | None = None
    billing_postal_code: str | None = None
    billing_country: str | None = None

    created_at: datetime

    class Config:
        from_attributes = True


class PaymentMethodListResponse(BaseModel):
    """Response schema for list of payment methods."""

    payment_methods: list[PaymentMethodResponse]
    total: int


class PaymentMethodSetDefault(BaseModel):
    """Schema for setting a payment method as default."""

    payment_method_id: UUID


# ============================================================================
# Subscription Schemas
# ============================================================================


class SubscriptionCreate(BaseModel):
    """Schema for creating a subscription."""

    plan: SubscriptionPlanEnum = Field(..., description="Subscription plan to subscribe to")
    payment_method_id: UUID | None = Field(
        None, description="Payment method to use (optional for free plan)"
    )


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription."""

    plan: SubscriptionPlanEnum | None = None
    cancel_at_period_end: bool | None = None


class SubscriptionResponse(BaseModel):
    """Response schema for subscription."""

    id: UUID
    plan: SubscriptionPlanEnum
    status: SubscriptionStatusEnum
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool
    price_amount: float | None = None
    price_currency: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Payment History Schemas
# ============================================================================


class PaymentHistoryResponse(BaseModel):
    """Response schema for payment history."""

    id: UUID
    amount: float
    currency: str
    status: PaymentStatusEnum
    description: str | None = None
    invoice_url: str | None = None
    receipt_url: str | None = None
    failure_message: str | None = None
    refunded_amount: float | None = None  # For partial refund tracking
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentHistoryListResponse(BaseModel):
    """Response schema for list of payment history."""

    payments: list[PaymentHistoryResponse]
    total: int


class PaymentHistoryStatsResponse(BaseModel):
    """Response schema for payment history statistics (aggregated)."""

    total_spent: float = Field(..., description="Total amount spent (succeeded payments)")
    total_payments: int = Field(..., description="Total number of payments")
    successful_payments: int = Field(..., description="Number of successful payments")
    failed_payments: int = Field(..., description="Number of failed payments")
    pending_payments: int = Field(..., description="Number of pending payments")
    refunded_payments: int = Field(..., description="Number of refunded payments")
    currency: str = Field(default="usd", description="Primary currency")


# ============================================================================
# Stripe Integration Schemas
# ============================================================================


class SetupIntentResponse(BaseModel):
    """Response schema for Stripe SetupIntent creation."""

    client_secret: str
    customer_id: str


class StripeWebhookEvent(BaseModel):
    """Schema for incoming Stripe webhook event."""

    type: str
    data: dict


# ============================================================================
# Plan Pricing Info
# ============================================================================


class PlanInfo(BaseModel):
    """Information about a subscription plan."""

    plan: SubscriptionPlanEnum
    name: str
    price_monthly: float
    price_yearly: float
    currency: str = "usd"
    features: list[str]

    # Limits - Single Source of Truth
    project_limit: int = Field(..., description="Maximum projects allowed (9999 = unlimited)")
    member_limit: int = Field(..., description="Maximum team members allowed (9999 = unlimited)")

    # Visual/Marketing config
    original_price: float | None = Field(
        None, description="Original price before discount (for strikethrough)"
    )
    discount_percent: int = Field(0, description="Current discount percentage")
    badge: str | None = Field(None, description="Badge text like 'Popular', 'Best Value'")
    badge_color: str | None = Field(None, description="Badge color class")
    color: str = Field("text-gray-500", description="Plan accent color class")
    is_limited_offer: bool = Field(False, description="Whether this is a limited time offer")


class PlansListResponse(BaseModel):
    """Response schema for available plans."""

    plans: list[PlanInfo]


# Pre-defined plan information - SINGLE SOURCE OF TRUTH
PLAN_DETAILS = {
    SubscriptionPlanEnum.FREE: PlanInfo(
        plan=SubscriptionPlanEnum.FREE,
        name="Free",
        price_monthly=0.0,
        price_yearly=0.0,
        project_limit=2,
        member_limit=3,
        original_price=None,
        discount_percent=0,
        badge=None,
        badge_color=None,
        color="text-gray-500",
        is_limited_offer=False,
        features=[
            "Up to 2 projects",
            "Up to 3 team members",
            "500 MB storage",
            "Basic analytics",
            "7-day task history",
        ],
    ),
    SubscriptionPlanEnum.STARTER: PlanInfo(
        plan=SubscriptionPlanEnum.STARTER,
        name="Starter",
        price_monthly=2.99,
        price_yearly=29.0,
        project_limit=5,
        member_limit=5,
        original_price=4.99,
        discount_percent=40,
        badge="40% OFF",
        badge_color="bg-red-500",
        color="text-blue-500",
        is_limited_offer=True,
        features=[
            "Up to 5 projects",
            "Up to 5 team members",
            "2 GB storage",
            "Standard analytics",
            "30-day task history",
            "Read-only API access",
            "Email support",
        ],
    ),
    SubscriptionPlanEnum.PRO: PlanInfo(
        plan=SubscriptionPlanEnum.PRO,
        name="Pro",
        price_monthly=6.99,
        price_yearly=69.0,
        project_limit=15,
        member_limit=15,
        original_price=9.99,
        discount_percent=30,
        badge="Popular",
        badge_color="bg-gradient-to-r from-purple-500 to-pink-500",
        color="text-emerald-500",
        is_limited_offer=True,
        features=[
            "Up to 15 projects",
            "Up to 15 team members",
            "10 GB storage",
            "Advanced analytics",
            "90-day task history",
            "Full API access",
            "Slack & Webhook integrations",
            "Priority support",
        ],
    ),
    SubscriptionPlanEnum.ENTERPRISE: PlanInfo(
        plan=SubscriptionPlanEnum.ENTERPRISE,
        name="Enterprise",
        price_monthly=14.99,
        price_yearly=149.0,
        project_limit=9999,
        member_limit=9999,
        original_price=24.99,
        discount_percent=40,
        badge="Best Value",
        badge_color="bg-gradient-to-r from-amber-500 to-orange-500",
        color="text-indigo-500",
        is_limited_offer=True,
        features=[
            "Unlimited projects",
            "Unlimited team members",
            "50 GB storage",
            "Custom reports",
            "Unlimited task history",
            "Full API + higher rate limit",
            "SSO integration",
            "Audit logs",
            "24/7 support",
        ],
    ),
}
