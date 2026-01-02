# ADR-0004: Stripe Payment Integration

## Status

Accepted

## Date

2026-01-02

## Context

Insight-Flow requires a subscription billing system with:
- Multiple pricing tiers (Free, Pro, Enterprise)
- Recurring monthly/yearly billing
- Secure payment method storage
- Webhook-based event handling
- Graceful downgrade handling

The payment system must be:
- PCI DSS compliant (no card data on our servers)
- Reliable with idempotent operations
- Auditable for financial compliance

## Decision

Integrate **Stripe** as the payment provider with:We

### Architecture Components

1. **PaymentService** (1500+ lines): Central service for all Stripe operations
2. **Distributed Locks**: Redis-based locks to prevent race conditions
3. **Idempotency Keys**: Prevent duplicate charges on retries
4. **Webhook Handler**: Process subscription lifecycle events
5. **Audit Logging**: Track all payment operations

### Key Patterns

```python
# Idempotency for safe retries
idempotency_key = f"sub_{user_id}_{plan}_{timestamp}"

# Distributed lock for concurrent requests
async with payment_lock(user_id):
    await process_subscription_change()
```

### Database Models

- `Subscription`: User subscription state
- `PaymentMethod`: Stored payment methods (Stripe tokens only)
- `PaymentHistory`: Transaction records
- `WebhookEventLog`: Idempotent webhook processing

## Consequences

### Positive

- PCI compliance handled by Stripe
- Robust webhook system for async events
- Built-in retry and idempotency support
- Excellent documentation and SDKs
- Customer portal for self-service

### Negative

- Transaction fees (2.9% + $0.30 per transaction)
- Vendor lock-in for payment processing
- Webhook delivery can be delayed
- Complex state management for subscriptions

### Neutral

- Requires Stripe account and API keys
- Webhook endpoint must be publicly accessible
- Test mode requires separate API keys

## Alternatives Considered

### Alternative 1: Paddle

Rejected because:
- Higher fees for our transaction volume
- Less flexible for SaaS pricing models
- Smaller developer community

### Alternative 2: LemonSqueezy

Considered but rejected because:
- Newer platform, less mature
- Limited enterprise features
- Stripe has better async Python support

### Alternative 3: Self-hosted Billing

Rejected because:
- PCI compliance burden
- Security risks of handling card data
- Significant development effort

## References

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Webhooks Best Practices](https://stripe.com/docs/webhooks/best-practices)
- [Stripe Idempotency Keys](https://stripe.com/docs/api/idempotent_requests)
