# Architecture Decision Records (ADRs)

This directory contains all Architecture Decision Records for the Insight-Flow project.

## What is an ADR?

An Architecture Decision Record captures an important architectural decision made along with its context and consequences.

## ADR Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| [ADR-0001](0001-use-fastapi-backend.md) | Use FastAPI as Backend Framework | Accepted | 2026-01-02 |
| [ADR-0002](0002-jwt-httponly-cookies.md) | JWT Authentication with HttpOnly Cookies | Accepted | 2026-01-02 |
| [ADR-0003](0003-zustand-state-management.md) | Zustand for Frontend State Management | Accepted | 2026-01-02 |
| [ADR-0004](0004-stripe-payment-integration.md) | Stripe Payment Integration | Accepted | 2026-01-02 |
| [ADR-0005](0005-redis-caching-strategy.md) | Redis Caching Strategy with Fallback | Accepted | 2026-01-02 |

## Creating a New ADR

1. Copy `template.md` to `XXXX-title-with-dashes.md`
2. Fill in all sections
3. Submit for review via PR
4. Update the index above

## Template

See [template.md](template.md) for the ADR template.
