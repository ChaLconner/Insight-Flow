"""
Performance monitoring middleware with request latency metrics.

Collects request duration metrics for observability and Prometheus integration.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logger import setup_logger

logger = setup_logger("performance")


@dataclass
class RequestMetrics:
    """Container for request latency metrics."""

    # Histogram buckets in seconds
    BUCKETS: tuple = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    # Metrics storage
    request_count: dict = field(default_factory=lambda: defaultdict(int))
    request_latency_sum: dict = field(default_factory=lambda: defaultdict(float))
    request_latency_bucket: dict = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    error_count: dict = field(default_factory=lambda: defaultdict(int))

    _lock: Lock = field(default_factory=Lock)

    def record(self, method: str, path: str, status_code: int, duration: float) -> None:
        """Record a request metric."""
        # Normalize path to reduce cardinality (remove IDs)
        normalized_path = self._normalize_path(path)
        key = f"{method}:{normalized_path}"

        with self._lock:
            self.request_count[key] += 1
            self.request_latency_sum[key] += duration

            # Record in histogram buckets
            for bucket in self.BUCKETS:
                if duration <= bucket:
                    self.request_latency_bucket[key][bucket] += 1
            # +Inf bucket
            self.request_latency_bucket[key][float("inf")] += 1

            # Track errors
            if status_code >= 400:
                self.error_count[key] += 1

    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing UUIDs and IDs with placeholders."""
        import re

        # Replace UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
            flags=re.IGNORECASE,
        )
        # Replace numeric IDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
        return path

    def get_prometheus_metrics(self) -> list[str]:
        """Generate Prometheus-format metrics."""
        metrics = []

        with self._lock:
            # Request count
            metrics.extend(
                [
                    "# HELP http_requests_total Total HTTP requests",
                    "# TYPE http_requests_total counter",
                ]
            )
            for key, count in self.request_count.items():
                method, path = key.split(":", 1)
                metrics.append(f'http_requests_total{{method="{method}",path="{path}"}} {count}')

            # Request latency sum
            metrics.extend(
                [
                    "# HELP http_request_duration_seconds_sum Total request duration",
                    "# TYPE http_request_duration_seconds_sum counter",
                ]
            )
            for key, total in self.request_latency_sum.items():
                method, path = key.split(":", 1)
                metrics.append(
                    f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total:.6f}'
                )

            # Request latency histogram
            metrics.extend(
                [
                    "# HELP http_request_duration_seconds Request duration histogram",
                    "# TYPE http_request_duration_seconds histogram",
                ]
            )
            for key, buckets in self.request_latency_bucket.items():
                method, path = key.split(":", 1)
                cumulative = 0
                for bucket in self.BUCKETS:
                    cumulative += buckets.get(bucket, 0)
                    metrics.append(
                        f'http_request_duration_seconds_bucket'
                        f'{{method="{method}",path="{path}",le="{bucket}"}} {cumulative}'
                    )
                cumulative += buckets.get(float("inf"), 0) - cumulative
                metrics.append(
                    f'http_request_duration_seconds_bucket'
                    f'{{method="{method}",path="{path}",le="+Inf"}} {self.request_count[key]}'
                )

            # Error count
            metrics.extend(
                [
                    "# HELP http_errors_total Total HTTP errors (4xx, 5xx)",
                    "# TYPE http_errors_total counter",
                ]
            )
            for key, count in self.error_count.items():
                method, path = key.split(":", 1)
                metrics.append(f'http_errors_total{{method="{method}",path="{path}"}} {count}')

        return metrics

    def get_stats(self) -> dict[str, Any]:
        """Get summary statistics."""
        with self._lock:
            total_requests = sum(self.request_count.values())
            total_errors = sum(self.error_count.values())
            avg_latency = (
                sum(self.request_latency_sum.values()) / total_requests if total_requests > 0 else 0
            )
            return {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": total_errors / total_requests if total_requests > 0 else 0,
                "avg_latency_ms": round(avg_latency * 1000, 2),
                "endpoints_tracked": len(self.request_count),
            }


# Global metrics instance
_request_metrics = RequestMetrics()


def get_request_metrics() -> RequestMetrics:
    """Get the global request metrics instance."""
    return _request_metrics


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking request performance and collecting metrics.

    Features:
    - Request duration tracking
    - Prometheus-compatible histogram metrics
    - Slow request logging
    - Error rate tracking
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        process_time = time.time() - start_time
        process_time_ms = round(process_time * 1000, 2)

        # Record metrics
        _request_metrics.record(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=process_time,
        )

        # Log slow requests (> 1 second)
        if process_time > 1.0:
            logger.warning(
                f"Slow Request: {request.method} {request.url.path} "
                f"took {process_time_ms}ms - Status: {response.status_code}"
            )

        # Add header for debugging
        response.headers["X-Process-Time"] = str(process_time_ms)

        return response
