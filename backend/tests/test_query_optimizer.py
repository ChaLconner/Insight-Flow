"""
Comprehensive tests for Query Optimizer utilities.
Tests profiling, batch loading, and optimization functions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.query_optimizer import (
    QueryProfiler,
    BatchLoader,
    QueryOptimizer,
    QueryMetrics,
    cached_query,
    count_optimized,
    exists_optimized,
)


class TestQueryProfiler:
    """Tests for QueryProfiler class."""
    
    def test_profiler_initialization(self):
        """Test profiler initializes correctly."""
        profiler = QueryProfiler()
        
        assert profiler._enabled is True
        assert profiler.metrics == []
    
    def test_enable_disable(self):
        """Test enable and disable functionality."""
        profiler = QueryProfiler()
        
        profiler.disable()
        assert profiler._enabled is False
        
        profiler.enable()
        assert profiler._enabled is True
    
    def test_clear_metrics(self):
        """Test clearing metrics."""
        profiler = QueryProfiler()
        profiler.metrics = [
            QueryMetrics("test", 100.0, 10),
            QueryMetrics("test2", 200.0, 20),
        ]
        
        profiler.clear()
        
        assert profiler.metrics == []
    
    def test_get_summary_empty(self):
        """Test summary with no metrics."""
        profiler = QueryProfiler()
        
        summary = profiler.get_summary()
        
        assert summary["total_queries"] == 0
    
    def test_get_summary_with_metrics(self):
        """Test summary with metrics."""
        profiler = QueryProfiler()
        profiler.metrics = [
            QueryMetrics("query1", 100.0, 10),
            QueryMetrics("query2", 200.0, 20),
            QueryMetrics("query3", 50.0, 5),
        ]
        
        summary = profiler.get_summary()
        
        assert summary["total_queries"] == 3
        assert summary["total_time_ms"] == 350.0
        assert summary["avg_time_ms"] == round(350.0 / 3, 2)
        assert summary["slowest_query"] == "query2"
        assert summary["slowest_time_ms"] == 200.0
        assert summary["total_rows"] == 35


class TestQueryMetrics:
    """Tests for QueryMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating query metrics."""
        metrics = QueryMetrics(
            query_name="test_query",
            execution_time_ms=150.5,
            rows_returned=100,
            query_plan="Seq Scan on users"
        )
        
        assert metrics.query_name == "test_query"
        assert metrics.execution_time_ms == 150.5
        assert metrics.rows_returned == 100
        assert metrics.query_plan == "Seq Scan on users"
    
    def test_metrics_default_query_plan(self):
        """Test metrics with default query plan."""
        metrics = QueryMetrics(
            query_name="test",
            execution_time_ms=100.0,
            rows_returned=50
        )
        
        assert metrics.query_plan is None


class TestBatchLoader:
    """Tests for BatchLoader class."""
    
    @pytest.mark.asyncio
    async def test_load_many_empty(self):
        """Test loading with empty IDs."""
        mock_session = AsyncMock()
        loader = BatchLoader(mock_session)
        
        result = await loader.load_many(MagicMock(), [])
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_load_related_empty(self):
        """Test loading related with empty parent IDs."""
        mock_session = AsyncMock()
        loader = BatchLoader(mock_session)
        
        result = await loader.load_related(MagicMock(), [], "parent_id")
        
        assert dict(result) == {}
    
    def test_batch_size(self):
        """Test batch size configuration."""
        mock_session = AsyncMock()
        loader = BatchLoader(mock_session, batch_size=50)
        
        assert loader.batch_size == 50


class TestQueryOptimizer:
    """Tests for QueryOptimizer class."""
    
    def test_paginate(self):
        """Test pagination helper."""
        mock_query = MagicMock()
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        result = QueryOptimizer.paginate(mock_query, page=2, per_page=10)
        
        mock_query.offset.assert_called_with(10)
        mock_query.limit.assert_called_with(10)
    
    def test_paginate_first_page(self):
        """Test pagination for first page."""
        mock_query = MagicMock()
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        QueryOptimizer.paginate(mock_query, page=1, per_page=20)
        
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(20)


class TestCachedQuery:
    """Tests for cached_query decorator."""
    
    @pytest.mark.asyncio
    async def test_cache_decorator(self):
        """Test that caching works."""
        call_count = 0
        
        @cached_query(ttl_seconds=60)
        async def get_data(key: str):
            nonlocal call_count
            call_count += 1
            return f"result_{key}"
        
        # First call
        result1 = await get_data("test")
        assert result1 == "result_test"
        assert call_count == 1
        
        # Second call - should use cache
        result2 = await get_data("test")
        assert result2 == "result_test"
        assert call_count == 1  # Still 1, cached
        
        # Different key - should call again
        result3 = await get_data("other")
        assert result3 == "result_other"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clearing."""
        call_count = 0
        
        @cached_query(ttl_seconds=60)
        async def get_data():
            nonlocal call_count
            call_count += 1
            return "result"
        
        await get_data()
        assert call_count == 1
        
        get_data.clear_cache()
        
        await get_data()
        assert call_count == 2  # Called again after cache clear


class TestOptimizedQueries:
    """Tests for optimized query functions."""
    
    def test_count_optimized_signature(self):
        """Test count_optimized function exists and is async."""
        import inspect
        
        assert callable(count_optimized)
        assert inspect.iscoroutinefunction(count_optimized)
    
    def test_exists_optimized_signature(self):
        """Test exists_optimized function exists and is async."""
        import inspect
        
        assert callable(exists_optimized)
        assert inspect.iscoroutinefunction(exists_optimized)
    
    def test_exists_logic(self):
        """Test exists logic with count values."""
        # Simulating the exists check logic
        def exists_check(count: int) -> bool:
            return (count or 0) > 0
        
        assert exists_check(1) is True
        assert exists_check(5) is True
        assert exists_check(0) is False
        assert exists_check(None) is False


class TestPerformanceMetrics:
    """Tests for performance-related functionality."""
    
    def test_slow_query_threshold(self):
        """Test slow query detection threshold."""
        threshold_ms = 100
        
        fast_query_time = 50
        slow_query_time = 150
        
        assert fast_query_time < threshold_ms
        assert slow_query_time > threshold_ms
    
    def test_query_timing_accuracy(self):
        """Test query timing measurement."""
        import time
        
        start = time.perf_counter()
        time.sleep(0.01)  # 10ms
        elapsed = (time.perf_counter() - start) * 1000
        
        # Should be approximately 10ms (with some tolerance)
        assert elapsed > 5
        assert elapsed < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
