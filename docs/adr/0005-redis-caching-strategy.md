# ADR-0005: Redis Caching Strategy with In-Memory Fallback

## Status

Accepted

## Date

2026-01-02

## Context

The application requires caching to:
- Reduce database load for frequently accessed data
- Improve API response times
- Support rate limiting across multiple workers
- Enable distributed locks for concurrent operations

The solution must work in:
- Local development (may not have Redis)
- Single-worker deployments
- Multi-worker production environments

## Decision

Implement a **hybrid caching strategy** with:
- **Primary**: Redis (when `REDIS_URL` is configured)
- **Fallback**: In-memory LRU cache (development/single worker)

### Cache Service Architecture

```python
class CacheService:
    def __init__(self):
        if settings.cache.redis_url:
            self.backend = RedisBackend(redis_url)
        else:
            self.backend = InMemoryBackend()
```

### Components Using Cache

1. **CacheService**: General-purpose caching
2. **RateLimiter**: IP and user-based rate limiting
3. **DistributedLocks**: Payment operation locks
4. **SessionStore**: Token blacklist (Redis only)

### Cache Patterns

- **Cache-Aside**: Application manages cache explicitly
- **TTL-Based Expiry**: All entries have expiration
- **Prefix Namespacing**: `insight:cache:`, `insight:lock:`

## Consequences

### Positive

- Zero-dependency development (works without Redis)
- Graceful degradation if Redis unavailable
- Consistent API regardless of backend
- Statistics tracking (hits, misses, hit rate)

### Negative

- In-memory cache doesn't share across workers
- Rate limiting less accurate in multi-worker without Redis
- Distributed locks fallback to local locks (race condition risk)

### Neutral

- Configuration determines behavior
- Cache hit rates may vary between environments

## Alternatives Considered

### Alternative 1: Redis Only (Required)

Rejected because:
- Adds complexity for local development
- Docker Compose required for simple testing
- Fails hard if Redis unavailable

### Alternative 2: Memcached

Rejected because:
- Less feature-rich than Redis
- No native support for locks
- Redis already needed for other features

### Alternative 3: PostgreSQL as Cache

Rejected because:
- Adds load to primary database
- Less performant for cache workloads
- Not designed for ephemeral data

## References

- [Redis Best Practices](https://redis.io/docs/management/optimization/)
- [Cache-Aside Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/cache-aside)
- [Python Redis Library](https://redis-py.readthedocs.io/)
