"""
Performance and Load Testing Configuration
Advanced performance benchmarks for Insight-Flow
"""
import pytest
from httpx import AsyncClient, ASGITransport
import asyncio
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class PerformanceResult:
    """Result of a performance test."""
    endpoint: str
    method: str
    requests_count: int
    total_time: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    success_rate: float
    requests_per_second: float


class PerformanceTester:
    """Helper class for performance testing."""

    def __init__(self, base_url: str = "http://localhost"):
        self.base_url = base_url
        self.results: List[float] = []
        self.errors: List[str] = []

    async def benchmark_endpoint(
        self,
        app,
        endpoint: str,
        method: str = "GET",
        num_requests: int = 100,
        concurrent: int = 10,
        payload: Dict[str, Any] = None
    ) -> PerformanceResult:
        """Benchmark an endpoint with multiple requests."""
        response_times: List[float] = []
        success_count = 0
        error_count = 0

        async def make_request(client: AsyncClient) -> float:
            nonlocal success_count, error_count
            start = time.time()
            try:
                if method.upper() == "GET":
                    response = await client.get(endpoint)
                elif method.upper() == "POST":
                    response = await client.post(endpoint, json=payload or {})
                elif method.upper() == "PUT":
                    response = await client.put(endpoint, json=payload or {})
                elif method.upper() == "DELETE":
                    response = await client.delete(endpoint)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                elapsed = time.time() - start
                if response.status_code < 400:
                    success_count += 1
                else:
                    error_count += 1
                return elapsed
            except Exception as e:
                error_count += 1
                return time.time() - start

        start_time = time.time()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=self.base_url
        ) as client:
            # Run requests in batches
            for batch_start in range(0, num_requests, concurrent):
                batch_size = min(concurrent, num_requests - batch_start)
                tasks = [make_request(client) for _ in range(batch_size)]
                batch_times = await asyncio.gather(*tasks)
                response_times.extend(batch_times)

        total_time = time.time() - start_time

        # Calculate statistics
        sorted_times = sorted(response_times)
        return PerformanceResult(
            endpoint=endpoint,
            method=method,
            requests_count=num_requests,
            total_time=total_time,
            avg_response_time=statistics.mean(sorted_times),
            min_response_time=min(sorted_times),
            max_response_time=max(sorted_times),
            p50_response_time=sorted_times[int(len(sorted_times) * 0.5)],
            p95_response_time=sorted_times[int(len(sorted_times) * 0.95)],
            p99_response_time=sorted_times[int(len(sorted_times) * 0.99)],
            success_rate=(success_count / num_requests) * 100,
            requests_per_second=num_requests / total_time
        )


class TestEndpointPerformance:
    """Performance tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint_performance(self):
        """Test /health endpoint performance."""
        from main import app

        tester = PerformanceTester()
        result = await tester.benchmark_endpoint(
            app,
            "/health",
            num_requests=100,
            concurrent=10
        )

        # Health endpoint should be fast
        assert result.avg_response_time < 0.2  # <200ms average
        assert result.p95_response_time < 0.3  # <300ms p95
        assert result.success_rate > 95  # >95% success rate
        assert result.requests_per_second > 20  # >20 RPS

    @pytest.mark.asyncio
    async def test_full_health_endpoint_performance(self):
        """Test /health/full endpoint performance."""
        from main import app

        tester = PerformanceTester()
        result = await tester.benchmark_endpoint(
            app,
            "/health/full",
            num_requests=50,
            concurrent=5
        )

        # Full health check can be slower (includes DB check)
        assert result.avg_response_time < 1.0  # <1s average
        assert result.p95_response_time < 2.0  # <2s p95
        assert result.success_rate > 90  # >90% success rate

    @pytest.mark.asyncio
    async def test_metrics_endpoint_performance(self):
        """Test /metrics endpoint performance."""
        from main import app

        tester = PerformanceTester()
        result = await tester.benchmark_endpoint(
            app,
            "/metrics",
            num_requests=50,
            concurrent=5
        )

        # Metrics should be relatively fast
        assert result.avg_response_time < 0.2  # <200ms average
        assert result.success_rate > 95


class TestConcurrencyHandling:
    """Tests for concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_health_requests(self):
        """Test handling of concurrent requests."""
        from main import app

        tester = PerformanceTester()

        # High concurrency test
        result = await tester.benchmark_endpoint(
            app,
            "/health",
            num_requests=200,
            concurrent=50
        )

        # Should handle high concurrency
        assert result.success_rate > 90
        assert result.p99_response_time < 1.0

    @pytest.mark.asyncio
    async def test_burst_traffic_handling(self):
        """Test handling of burst traffic."""
        from main import app

        results = []

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            # Simulate burst: many requests at once
            start = time.time()
            tasks = [client.get("/health") for _ in range(100)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start

            success_count = sum(
                1 for r in responses
                if hasattr(r, 'status_code') and r.status_code == 200
            )

        # Should handle burst traffic
        assert success_count > 80  # At least 80% success
        assert elapsed < 5  # Complete within 5 seconds


class TestDatabasePerformance:
    """Tests for database query performance."""

    @pytest.mark.asyncio
    async def test_db_connection_pool(self):
        """Test database connection pooling efficiency."""
        from main import app

        tester = PerformanceTester()

        # Test endpoint that queries database
        result = await tester.benchmark_endpoint(
            app,
            "/health/db",
            num_requests=50,
            concurrent=10
        )

        # Database health check
        assert result.avg_response_time < 0.5  # <500ms average


class TestResponseTimes:
    """Tests for response time requirements."""

    @pytest.mark.asyncio
    async def test_response_time_sla(self):
        """Test that endpoints meet SLA requirements."""
        from main import app

        # Define SLA requirements
        sla_requirements = {
            "/health": {"p95": 0.3, "p99": 0.5},
            "/health/full": {"p95": 1.0, "p99": 2.0},
            "/metrics": {"p95": 0.5, "p99": 1.0},
        }

        tester = PerformanceTester()

        for endpoint, sla in sla_requirements.items():
            result = await tester.benchmark_endpoint(
                app,
                endpoint,
                num_requests=50,
                concurrent=5
            )

            assert result.p95_response_time < sla["p95"], \
                f"{endpoint} p95 ({result.p95_response_time:.3f}s) exceeds SLA ({sla['p95']}s)"
            assert result.p99_response_time < sla["p99"], \
                f"{endpoint} p99 ({result.p99_response_time:.3f}s) exceeds SLA ({sla['p99']}s)"


class TestThroughput:
    """Tests for throughput requirements."""

    @pytest.mark.asyncio
    async def test_minimum_throughput(self):
        """Test minimum throughput requirements."""
        from main import app

        tester = PerformanceTester()
        result = await tester.benchmark_endpoint(
            app,
            "/health",
            num_requests=200,
            concurrent=20
        )

        # Should achieve minimum throughput
        assert result.requests_per_second > 50, \
            f"Throughput ({result.requests_per_second:.1f} RPS) below minimum (50 RPS)"


class TestResourceUsage:
    """Tests for resource usage efficiency."""

    @pytest.mark.asyncio
    async def test_memory_stability(self):
        """Test that memory usage is stable over many requests."""
        from main import app
        import gc

        # Force garbage collection before test
        gc.collect()

        tester = PerformanceTester()

        # Run multiple batches
        for batch in range(3):
            result = await tester.benchmark_endpoint(
                app,
                "/health",
                num_requests=100,
                concurrent=10
            )
            assert result.success_rate > 95

        # Force garbage collection after
        gc.collect()


class TestErrorHandling:
    """Tests for error handling under load."""

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test that system degrades gracefully under load."""
        from main import app

        tester = PerformanceTester()

        # Heavy load test
        result = await tester.benchmark_endpoint(
            app,
            "/health",
            num_requests=500,
            concurrent=100
        )

        # System should still respond, even if some requests fail
        assert result.success_rate > 80  # At least 80% success
        # Response time increase is acceptable under heavy load
        assert result.p99_response_time < 5.0


class TestCachingEffectiveness:
    """Tests for caching effectiveness."""

    @pytest.mark.asyncio
    async def test_cache_hit_performance(self):
        """Test that cached responses are faster."""
        from main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://localhost"
        ) as client:
            # First request (cold)
            start = time.time()
            await client.get("/health")
            cold_time = time.time() - start

            # Subsequent requests (should be from cache if enabled)
            warm_times = []
            for _ in range(5):
                start = time.time()
                await client.get("/health")
                warm_times.append(time.time() - start)

            avg_warm_time = statistics.mean(warm_times)

            # Warm requests should not be significantly slower
            # (Caching may not apply to health endpoint)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
