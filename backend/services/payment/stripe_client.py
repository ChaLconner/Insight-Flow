"""
Stripe API client wrapper.

This module provides an abstraction layer over the Stripe API,
making it easier to:
- Mock in tests
- Replace with another payment provider in the future
- Centralize Stripe configuration and error handling
"""

import asyncio
from typing import Any, cast

import stripe
from stripe import Customer, PaymentMethod, SetupIntent, Subscription

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger("stripe_client")


class StripeClientError(Exception):
    """Base exception for Stripe client errors."""

    pass


class StripeNotConfiguredError(StripeClientError):
    """Raised when Stripe is not configured."""

    pass


class StripeClient:
    """
    Abstraction over Stripe API for payment operations.

    This client provides async-compatible methods for common Stripe operations.
    All blocking Stripe SDK calls are wrapped in run_in_executor.

    Usage:
        client = StripeClient()
        if client.is_configured:
            customer = await client.create_customer("user@example.com", "John Doe")
    """

    def __init__(self):
        settings = get_settings()
        self._configured = settings.stripe.is_configured

        if self._configured:
            stripe.api_key = settings.stripe.secret_key
            logger.info("StripeClient initialized with API key")
        else:
            logger.warning("StripeClient: Stripe not configured")

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return self._configured

    def _check_configured(self) -> None:
        """Raise error if Stripe is not configured."""
        if not self._configured:
            raise StripeNotConfiguredError("Stripe is not configured")

    async def _run_stripe(self, func, *args, idempotency_key: str | None = None, **kwargs) -> Any:
        """
        Run a blocking Stripe SDK call in executor.

        Args:
            func: Stripe SDK function to call
            *args: Positional arguments
            idempotency_key: Optional idempotency key for retries
            **kwargs: Keyword arguments

        Returns:
            Result from Stripe API
        """
        self._check_configured()

        loop = asyncio.get_running_loop()

        def execute():
            if idempotency_key:
                return func(*args, idempotency_key=idempotency_key, **kwargs)
            return func(*args, **kwargs)

        try:
            return await loop.run_in_executor(None, execute)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {e}")
            raise

    # ===========================================
    # Customer Operations
    # ===========================================

    async def create_customer(
        self,
        email: str,
        name: str | None = None,
        metadata: dict | None = None,
        idempotency_key: str | None = None,
    ) -> Customer:
        """
        Create a new Stripe customer.

        Args:
            email: Customer email
            name: Customer name (optional)
            metadata: Additional metadata (optional)
            idempotency_key: Idempotency key for retries

        Returns:
            Stripe Customer object
        """
        params: dict[str, Any] = {"email": email}
        if name:
            params["name"] = name
        if metadata:
            params["metadata"] = metadata

        return cast(Customer, await self._run_stripe(
            stripe.Customer.create, idempotency_key=idempotency_key, **params
        ))

    async def get_customer(self, customer_id: str) -> Customer | None:
        """Get a Stripe customer by ID."""
        try:
            return cast(Customer | None, await self._run_stripe(stripe.Customer.retrieve, customer_id))
        except stripe.error.InvalidRequestError:
            return None

    async def update_customer(self, customer_id: str, **kwargs) -> Customer:
        """Update a Stripe customer."""
        return cast(Customer, await self._run_stripe(stripe.Customer.modify, customer_id, **kwargs))

    # ===========================================
    # Payment Method Operations
    # ===========================================

    async def create_setup_intent(
        self, customer_id: str, idempotency_key: str | None = None
    ) -> SetupIntent:
        """
        Create a SetupIntent for collecting payment method.

        Args:
            customer_id: Stripe customer ID
            idempotency_key: Idempotency key for retries

        Returns:
            SetupIntent with client_secret for frontend
        """
        return cast(SetupIntent, await self._run_stripe(
            stripe.SetupIntent.create,
            customer=customer_id,
            payment_method_types=["card"],
            idempotency_key=idempotency_key,
        ))

    async def attach_payment_method(
        self, payment_method_id: str, customer_id: str
    ) -> PaymentMethod:
        """Attach a payment method to a customer."""
        return cast(PaymentMethod, await self._run_stripe(
            stripe.PaymentMethod.attach, payment_method_id, customer=customer_id
        ))

    async def detach_payment_method(self, payment_method_id: str) -> PaymentMethod:
        """Detach a payment method from its customer."""
        return cast(PaymentMethod, await self._run_stripe(stripe.PaymentMethod.detach, payment_method_id))

    async def list_payment_methods(
        self, customer_id: str, type: str = "card"
    ) -> list[PaymentMethod]:
        """List all payment methods for a customer."""
        result = await self._run_stripe(stripe.PaymentMethod.list, customer=customer_id, type=type)
        return list(result.data) if result else []

    async def set_default_payment_method(
        self, customer_id: str, payment_method_id: str
    ) -> Customer:
        """Set the default payment method for a customer."""
        return cast(Customer, await self._run_stripe(
            stripe.Customer.modify,
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        ))

    # ===========================================
    # Subscription Operations
    # ===========================================

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        default_payment_method: str | None = None,
        metadata: dict | None = None,
        idempotency_key: str | None = None,
    ) -> Subscription:
        """
        Create a new subscription.

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            default_payment_method: Payment method to use
            metadata: Additional metadata
            idempotency_key: Idempotency key

        Returns:
            Stripe Subscription object
        """
        params: dict[str, Any] = {
            "customer": customer_id,
        }
        if price_id:
            # Stripe expects a list of items for subscription creation
            # We cast to Any here because Stripe's type definitions are strict about Sequence[Collection[str]]
            # but accept list of dicts at runtime for 'items'
            params["items"] = cast(Any, [{"price": price_id}])
        if default_payment_method:
            params["default_payment_method"] = default_payment_method
        if metadata:
            params["metadata"] = metadata

        return cast(Subscription, await self._run_stripe(
            stripe.Subscription.create, idempotency_key=idempotency_key, **params
        ))

    async def get_subscription(self, subscription_id: str) -> Subscription | None:
        """Get a subscription by ID."""
        try:
            return cast(Subscription, await self._run_stripe(stripe.Subscription.retrieve, subscription_id))
        except stripe.error.InvalidRequestError:
            return None

    async def update_subscription(self, subscription_id: str, **kwargs) -> Subscription:
        """Update a subscription."""
        return cast(Subscription, await self._run_stripe(stripe.Subscription.modify, subscription_id, **kwargs))

    async def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> Subscription:
        """
        Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at end of billing period

        Returns:
            Updated subscription
        """
        if at_period_end:
            return cast(Subscription, await self._run_stripe(
                stripe.Subscription.modify, subscription_id, cancel_at_period_end=True
            ))
        else:
            return cast(Subscription, await self._run_stripe(stripe.Subscription.delete, subscription_id))

    # ===========================================
    # Webhook Verification
    # ===========================================

    def verify_webhook_signature(
        self, payload: bytes, sig_header: str, webhook_secret: str
    ) -> stripe.Event:
        """
        Verify and construct a webhook event.

        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header value
            webhook_secret: Webhook endpoint secret

        Returns:
            Verified Stripe Event

        Raises:
            stripe.error.SignatureVerificationError: If signature is invalid
        """
        return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)


# Singleton instance
_stripe_client: StripeClient | None = None


def get_stripe_client() -> StripeClient:
    """Get the singleton StripeClient instance."""
    global _stripe_client
    if _stripe_client is None:
        _stripe_client = StripeClient()
    return _stripe_client
