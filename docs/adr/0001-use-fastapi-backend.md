# ADR-0001: Use FastAPI as Backend Framework

## Status

Accepted

## Date

2026-01-02

## Context

Insight-Flow requires a robust Python backend framework that supports:
- High-performance async operations for real-time features
- Type safety and automatic API documentation
- Easy integration with PostgreSQL and Redis
- Modern Python features (3.11+)

The team has experience with Flask and Django, but needs a framework optimized for async I/O and API-first development.

## Decision

Use **FastAPI** as the primary backend framework with:
- **SQLAlchemy 2.0+** with async session support (asyncpg driver)
- **Pydantic v2** for request/response validation
- **Uvicorn** as the ASGI server
- **Alembic** for database migrations

## Consequences

### Positive

- Automatic OpenAPI (Swagger) documentation at `/docs`
- Native async/await support eliminates blocking I/O
- Pydantic validation catches errors at API boundary
- 40-50% faster than Flask for async workloads
- Built-in dependency injection system

### Negative

- Smaller ecosystem than Django (fewer pre-built packages)
- Team needs to learn async patterns
- No built-in admin panel (unlike Django)

### Neutral

- Requires explicit CORS, CSRF, and security middleware setup
- ORM choice is separate decision (not bundled like Django)

## Alternatives Considered

### Alternative 1: Django + Django REST Framework

Rejected because:
- Sync-first architecture requires workarounds for async
- Heavier framework for API-only service
- ORM is tightly coupled, harder to use async

### Alternative 2: Flask + Connexion

Rejected because:
- No native async support (requires Quart)
- Manual OpenAPI spec maintenance
- Less type safety without additional plugins

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Async Guide](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic v2 Migration](https://docs.pydantic.dev/latest/migration/)
