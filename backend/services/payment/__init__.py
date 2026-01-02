"""
Payment service package.

This package contains all payment-related services and utilities.
Structured for future extraction as a microservice.

Modules:
- stripe_client: Stripe API wrapper
- service: Main PaymentService (re-exported from parent)
- webhooks: Webhook handling (future)
"""

from services.payment_service import PaymentService

__all__ = ["PaymentService"]
