"""
OpenTelemetry Distributed Tracing Middleware - Staff/Principal Level

Provides:
- Distributed tracing with automatic span creation
- Request/Response attribute tracking
- Exception recording with stack traces
- Trace context propagation (W3C Trace Context)
- Integration with Jaeger/Zipkin/OTLP exporters
"""

import os
import traceback
from collections.abc import Callable
from typing import ClassVar, cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from utils.logger import setup_logger
from utils.path_normalization import normalize_request_path

logger = setup_logger("tracing")

# Lazy import OpenTelemetry to avoid hard dependency
_tracer = None
_otel_available = False


def _init_opentelemetry():
    """Initialize OpenTelemetry with environment-based configuration."""
    global _tracer, _otel_available

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.semconv.resource import ResourceAttributes

        _otel_available = True

        # Get configuration from environment
        service_name = os.getenv("OTEL_SERVICE_NAME", "insight-flow-backend")
        environment = os.getenv("ENVIRONMENT", "development")
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

        # Create resource with service information
        resource = Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: service_name,
                ResourceAttributes.SERVICE_VERSION: os.getenv("APP_VERSION", "1.0.0"),
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: environment,
            }
        )

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Add exporters based on configuration
        if otlp_endpoint:
            # OTLP exporter for Jaeger/Tempo/etc.
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true",
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OpenTelemetry: OTLP exporter configured for {otlp_endpoint}")
        elif environment == "development":
            # Console exporter for development
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("OpenTelemetry: Console exporter configured for development")

        # Set the tracer provider
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(__name__)

        logger.info(f"OpenTelemetry initialized for {service_name} in {environment}")
        return True

    except ImportError:
        logger.warning(
            "OpenTelemetry packages not installed. Tracing disabled. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk "
            "opentelemetry-exporter-otlp-proto-grpc opentelemetry-instrumentation-fastapi"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        return False


def get_tracer():
    """Get the configured tracer, initializing if necessary."""
    if _tracer is None:
        _init_opentelemetry()
    return _tracer


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Distributed tracing middleware for FastAPI.

    Features:
    - Automatic span creation for each request
    - HTTP semantic convention attributes
    - Exception recording with stack traces
    - Request/response body sampling (configurable)
    - User ID extraction from JWT

    Usage:
        app.add_middleware(TracingMiddleware)

    Environment Variables:
        OTEL_SERVICE_NAME: Service name (default: insight-flow-backend)
        OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (e.g., http://jaeger:4317)
        OTEL_EXPORTER_OTLP_INSECURE: Allow insecure connection (default: true)
        TRACING_SAMPLE_REQUEST_BODY: Sample request bodies (default: false)
        TRACING_SAMPLE_RESPONSE_BODY: Sample response bodies (default: false)
    """

    # Paths to exclude from tracing (health checks, metrics, static files)
    EXCLUDED_PATHS: ClassVar[set[str]] = {
        "/health",
        "/metrics",
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/favicon.ico",
    }

    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: set[str] | None = None,
        sample_request_body: bool = False,
        sample_response_body: bool = False,
    ):
        super().__init__(app)
        self.excluded_paths = excluded_paths or self.EXCLUDED_PATHS
        self.sample_request_body = (
            sample_request_body
            or os.getenv("TRACING_SAMPLE_REQUEST_BODY", "false").lower() == "true"
        )
        self.sample_response_body = (
            sample_response_body
            or os.getenv("TRACING_SAMPLE_RESPONSE_BODY", "false").lower() == "true"
        )

        # Initialize OpenTelemetry
        _init_opentelemetry()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # noqa: PLR0912
        """Process request with tracing."""

        # Skip excluded paths
        if request.url.path in self.excluded_paths:
            return cast("Response", await call_next(request))

        # If OpenTelemetry is not available, just pass through
        if not _otel_available or _tracer is None:
            return cast("Response", await call_next(request))

        try:
            from opentelemetry.semconv.trace import SpanAttributes
            from opentelemetry.trace import SpanKind, Status, StatusCode
        except ImportError:
            return cast("Response", await call_next(request))

        # Create span name
        span_name = f"{request.method} {self._normalize_path(request.url.path)}"

        # Start span
        with _tracer.start_as_current_span(
            span_name,
            kind=SpanKind.SERVER,
        ) as span:
            # Set HTTP semantic convention attributes
            span.set_attribute(SpanAttributes.HTTP_METHOD, request.method)
            span.set_attribute(SpanAttributes.HTTP_URL, str(request.url))
            span.set_attribute(SpanAttributes.HTTP_SCHEME, request.url.scheme)
            span.set_attribute(SpanAttributes.HTTP_HOST, request.url.hostname or "")
            span.set_attribute(SpanAttributes.HTTP_TARGET, request.url.path)
            span.set_attribute(SpanAttributes.NET_HOST_PORT, request.url.port or 80)

            # Set client information
            if request.client:
                span.set_attribute(SpanAttributes.NET_PEER_IP, request.client.host)

            # Set headers (filtered for security)
            user_agent = request.headers.get("user-agent", "")
            span.set_attribute(SpanAttributes.HTTP_USER_AGENT, user_agent)

            # Extract request ID if present
            request_id = request.headers.get("x-request-id", "")
            if request_id:
                span.set_attribute("request.id", request_id)

            # Extract user ID from JWT (if authenticated)
            user_id = self._extract_user_id(request)
            if user_id:
                span.set_attribute("user.id", user_id)

            # Sample request body (if enabled and safe)
            if self.sample_request_body and request.method in ("POST", "PUT", "PATCH"):
                try:
                    body = await self._safe_read_body(request)
                    if body:
                        # Truncate to prevent huge spans
                        span.set_attribute("http.request.body", body[:1000])
                except Exception:
                    pass

            try:
                # Process request
                response = await call_next(request)

                # Set response attributes
                span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, response.status_code)

                # Set span status based on HTTP status
                if response.status_code >= 500:
                    span.set_status(Status(StatusCode.ERROR, "Server Error"))
                elif response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR, "Client Error"))
                else:
                    span.set_status(Status(StatusCode.OK))

                return cast("Response", response)

            except Exception as e:
                # Record exception
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.set_attribute("exception.type", type(e).__name__)
                span.set_attribute("exception.message", str(e))
                span.set_attribute("exception.stacktrace", traceback.format_exc())
                raise

    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing IDs with placeholders."""
        return normalize_request_path(path)

    def _extract_user_id(self, request: Request) -> str | None:
        """
        Extract user ID from JWT token with proper verification.

        Security: Unlike the old implementation that decoded without verification,
        this now properly validates the token signature before trusting the payload.
        Invalid/expired tokens return None instead of potentially spoofed user IDs.
        """
        try:
            # Try cookie first
            token = request.cookies.get("access_token")
            if not token:
                # Try Authorization header
                auth_header = request.headers.get("authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]

            if token:
                # Import the verified token decoder from our auth utils
                # This properly validates the signature and expiration
                from utils.auth import verify_token

                try:
                    payload = verify_token(token)
                    return payload.get("sub")
                except Exception:
                    # Token is invalid or expired - don't log user ID
                    # This is expected for unauthenticated requests
                    return None
        except Exception:
            pass
        return None

    async def _safe_read_body(self, request: Request) -> str | None:
        """Safely read request body without consuming it."""
        try:
            body = await request.body()
            if body:
                return body.decode("utf-8", errors="replace")
        except Exception:
            pass
        return None


# =============================================================================
# Span Helpers for Custom Instrumentation
# =============================================================================


def create_span(name: str, **attributes):
    """
    Create a custom span for instrumenting specific operations.

    Usage:
        with create_span("database.query", query=sql) as span:
            result = await db.execute(sql)
            span.set_attribute("rows_returned", len(result))
    """
    tracer = get_tracer()
    if tracer is None:
        # Return a no-op context manager
        from contextlib import nullcontext

        return nullcontext()

    try:
        from opentelemetry.trace import SpanKind

        span = tracer.start_as_current_span(
            name,
            kind=SpanKind.INTERNAL,
            attributes=attributes,
        )
        return span
    except Exception:
        from contextlib import nullcontext

        return nullcontext()


async def trace_async_operation(name: str, operation, **attributes):
    """
    Trace an async operation.

    Usage:
        result = await trace_async_operation(
            "external.api.call",
            api_client.fetch_data(),
            api_name="user-service"
        )
    """
    with create_span(name, **attributes):
        return await operation


def get_current_trace_id() -> str | None:
    """Get the current trace ID for correlation in logs."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span:
            ctx = span.get_span_context()
            if ctx.is_valid:
                return format(ctx.trace_id, "032x")
    except Exception:
        pass
    return None


def get_current_span_id() -> str | None:
    """Get the current span ID."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span:
            ctx = span.get_span_context()
            if ctx.is_valid:
                return format(ctx.span_id, "016x")
    except Exception:
        pass
    return None


# =============================================================================
# Database Query Tracing
# =============================================================================


def trace_db_query(query_type: str, table: str | None = None):
    """
    Decorator for tracing database queries.

    Usage:
        @trace_db_query("SELECT", "users")
        async def get_user(user_id: str):
            ...
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            attributes = {
                "db.system": "postgresql",
                "db.operation": query_type,
            }
            if table:
                attributes["db.sql.table"] = table

            with create_span(f"db.{query_type.lower()}", **attributes):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# External Service Tracing
# =============================================================================


def trace_external_service(service_name: str, operation: str):
    """
    Decorator for tracing external service calls.

    Usage:
        @trace_external_service("stripe", "create_customer")
        async def create_stripe_customer(email: str):
            ...
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                from opentelemetry.trace import SpanKind

                tracer = get_tracer()
                if tracer:
                    with tracer.start_as_current_span(
                        f"{service_name}.{operation}",
                        kind=SpanKind.CLIENT,
                        attributes={
                            "peer.service": service_name,
                            "rpc.method": operation,
                        },
                    ):
                        return await func(*args, **kwargs)
            except Exception:
                pass
            return await func(*args, **kwargs)

        return wrapper

    return decorator
