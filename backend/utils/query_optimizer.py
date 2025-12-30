"""
Advanced Query Optimization Utilities.
Provides tools for optimizing database queries including:
- Query plan analysis
- N+1 query detection
- Batch loading utilities
- Query result caching
"""

import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from utils.logger import setup_logger

logger = setup_logger("query_optimizer")

T = TypeVar("T")


@dataclass
class QueryMetrics:
    """Metrics for a single query execution."""

    query_name: str
    execution_time_ms: float
    rows_returned: int
    query_plan: str | None = None


class QueryProfiler:
    """
    Profiles database queries and collects metrics.
    Useful for identifying slow queries and optimization opportunities.
    """

    def __init__(self):
        self.metrics: list[QueryMetrics] = []
        self._enabled = True

    def enable(self):
        """Enable query profiling."""
        self._enabled = True

    def disable(self):
        """Disable query profiling."""
        self._enabled = False

    def clear(self):
        """Clear collected metrics."""
        self.metrics = []

    async def profile_query(
        self, session: AsyncSession, query, query_name: str = "unnamed"
    ) -> tuple:
        """
        Execute and profile a query.

        Returns:
            Tuple of (result, metrics)
        """
        if not self._enabled:
            result = await session.execute(query)
            return result, None

        start_time = time.perf_counter()
        result = await session.execute(query)
        execution_time = (time.perf_counter() - start_time) * 1000

        rows = list(result.scalars().all())

        metrics = QueryMetrics(
            query_name=query_name,
            execution_time_ms=round(execution_time, 2),
            rows_returned=len(rows),
        )

        self.metrics.append(metrics)

        if execution_time > 100:  # Log slow queries
            logger.warning(f"Slow query detected: {query_name} took {execution_time:.2f}ms")

        return rows, metrics

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all profiled queries."""
        if not self.metrics:
            return {"total_queries": 0}

        total_time = sum(m.execution_time_ms for m in self.metrics)
        avg_time = total_time / len(self.metrics)
        slowest = max(self.metrics, key=lambda m: m.execution_time_ms)

        return {
            "total_queries": len(self.metrics),
            "total_time_ms": round(total_time, 2),
            "avg_time_ms": round(avg_time, 2),
            "slowest_query": slowest.query_name,
            "slowest_time_ms": slowest.execution_time_ms,
            "total_rows": sum(m.rows_returned for m in self.metrics),
        }


class BatchLoader:
    """
    Efficient batch loading to prevent N+1 queries.
    Groups multiple individual fetches into batch queries.
    """

    def __init__(self, session: AsyncSession, batch_size: int = 100):
        self.session = session
        self.batch_size = batch_size
        self._pending: dict[str, list] = defaultdict(list)
        self._results: dict[str, dict] = {}

    async def load_many(self, model, ids: list[Any], id_field: str = "id") -> dict[Any, Any]:
        """
        Load multiple records by IDs in a single query.

        Args:
            model: SQLAlchemy model class
            ids: List of IDs to load
            id_field: Name of the ID field

        Returns:
            Dictionary mapping ID to record
        """
        if not ids:
            return {}

        # Remove duplicates while preserving order
        unique_ids = list(dict.fromkeys(ids))

        # Batch the query
        results = {}
        for i in range(0, len(unique_ids), self.batch_size):
            batch_ids = unique_ids[i : i + self.batch_size]

            query = select(model).where(getattr(model, id_field).in_(batch_ids))
            result = await self.session.execute(query)

            for record in result.scalars().all():
                results[getattr(record, id_field)] = record

        return results

    async def load_related(self, model, parent_ids: list[Any], foreign_key: str) -> dict[Any, list]:
        """
        Load related records grouped by parent ID.

        Args:
            model: SQLAlchemy model class
            parent_ids: List of parent IDs
            foreign_key: Name of the foreign key field

        Returns:
            Dictionary mapping parent ID to list of related records
        """
        if not parent_ids:
            return defaultdict(list)

        unique_ids = list(dict.fromkeys(parent_ids))
        results = defaultdict(list)

        for i in range(0, len(unique_ids), self.batch_size):
            batch_ids = unique_ids[i : i + self.batch_size]

            query = select(model).where(getattr(model, foreign_key).in_(batch_ids))
            result = await self.session.execute(query)

            for record in result.scalars().all():
                parent_id = getattr(record, foreign_key)
                results[parent_id].append(record)

        return results


class QueryOptimizer:
    """
    Utilities for optimizing SQLAlchemy queries.
    """

    @staticmethod
    def with_eager_loading(query, *relationships):
        """
        Add eager loading for relationships to prevent N+1 queries.

        Args:
            query: Base query
            *relationships: Relationship names to eagerly load

        Returns:
            Query with selectinload options
        """
        for rel in relationships:
            query = query.options(selectinload(rel))
        return query

    @staticmethod
    def with_join_loading(query, *relationships):
        """
        Add JOIN loading for relationships.
        Better for single related objects.

        Args:
            query: Base query
            *relationships: Relationship names to join load

        Returns:
            Query with joinedload options
        """
        for rel in relationships:
            query = query.options(joinedload(rel))
        return query

    @staticmethod
    async def analyze_query(session: AsyncSession, query) -> str:
        """
        Get EXPLAIN ANALYZE output for a query.

        Args:
            session: Database session
            query: Query to analyze

        Returns:
            Query execution plan as string
        """
        try:
            # Get the compiled query
            compiled = query.compile(compile_kwargs={"literal_binds": True})
            sql = str(compiled)

            # Run EXPLAIN ANALYZE
            result = await session.execute(text(f"EXPLAIN ANALYZE {sql}"))

            plan_lines = [row[0] for row in result.fetchall()]
            return "\n".join(plan_lines)
        except Exception as e:
            return f"Could not analyze query: {e}"

    @staticmethod
    def paginate(query, page: int = 1, per_page: int = 20):
        """
        Add pagination to a query.

        Args:
            query: Base query
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Paginated query
        """
        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page)


def cached_query(ttl_seconds: int = 60):
    """
    Decorator for caching query results.
    Uses in-memory cache with TTL.

    Args:
        ttl_seconds: Time to live in seconds
    """
    cache: dict[str, tuple] = {}

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{args!s}:{kwargs!s}"

            # Check cache
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    return result

            # Execute and cache
            result = await func(*args, **kwargs)
            cache[key] = (result, time.time())

            return result

        wrapper.clear_cache = lambda: cache.clear()  # type: ignore
        return wrapper

    return decorator


async def count_optimized(session: AsyncSession, model) -> int:
    """
    Optimized count query that doesn't load actual records.

    Args:
        session: Database session
        model: SQLAlchemy model class

    Returns:
        Count of records
    """
    result = await session.execute(select(func.count()).select_from(model))
    return result.scalar() or 0


async def exists_optimized(session: AsyncSession, model, **filters) -> bool:
    """
    Check if a record exists without loading it.

    Args:
        session: Database session
        model: SQLAlchemy model class
        **filters: Field-value pairs to filter by

    Returns:
        True if record exists
    """
    query = select(func.count()).select_from(model)

    for field, value in filters.items():
        if hasattr(model, field):
            query = query.where(getattr(model, field) == value)

    result = await session.execute(query.limit(1))
    return (result.scalar() or 0) > 0


# Global profiler instance
query_profiler = QueryProfiler()
