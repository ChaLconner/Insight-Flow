import json
import logging
import os
from contextvars import ContextVar

# Context variable for request-scoped data
request_context: ContextVar[dict | None] = ContextVar("request_context", default=None)


def set_request_context(**kwargs) -> None:
    """Set request context for current async context."""
    current = request_context.get() or {}
    request_context.set({**current, **kwargs})


def clear_request_context() -> None:
    """Clear request context."""
    request_context.set({})


def _get_trace_context() -> dict:
    """
    Get trace and span IDs from OpenTelemetry if available.

    Returns dict with trace_id and span_id if available.
    """
    try:
        from middleware.tracing import get_current_span_id, get_current_trace_id

        trace_id = get_current_trace_id()
        span_id = get_current_span_id()
        if trace_id:
            return {"trace_id": trace_id, "span_id": span_id}
    except ImportError:
        pass
    except Exception:
        pass
    return {}


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging with OpenTelemetry trace correlation.
    Supports request_id, user_id, trace_id, span_id, and additional context.
    """

    def format(self, record):
        # Get current request context
        ctx = request_context.get() or {}

        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": os.getenv("OTEL_SERVICE_NAME", "insight-flow"),
            "environment": os.getenv("ENVIRONMENT", "development"),
        }

        # Add request context if available
        if ctx.get("request_id"):
            log_record["request_id"] = ctx["request_id"]
        if ctx.get("user_id"):
            log_record["user_id"] = ctx["user_id"]
        if ctx.get("path"):
            log_record["path"] = ctx["path"]
        if ctx.get("method"):
            log_record["method"] = ctx["method"]

        # Add OpenTelemetry trace context for correlation
        trace_ctx = _get_trace_context()
        if trace_ctx:
            log_record.update(trace_ctx)

        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_record.update(record.extra_fields)

        # Add source info if in debug or error
        if record.levelno >= logging.ERROR or os.getenv("DEBUG", "false").lower() == "true":
            log_record.update(
                {"file": record.filename, "line": record.lineno, "function": record.funcName}
            )

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, default=str)


def setup_logger(name: str, level: str | None = None) -> logging.Logger:
    """
    Setup logger with appropriate configuration based on environment.

    Args:
        name: Logger name
        level: Optional log level override

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set log level based on environment or parameter
    if level:
        log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        # Use DEBUG in development, INFO in production
        log_level = logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO

    logger.setLevel(log_level)

    # Avoid adding multiple handlers
    if logger.handlers:
        return logger

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Create formatter
    formatter: logging.Formatter
    if os.getenv("ENVIRONMENT") == "production":
        # Use JSON formatter for production
        formatter = JsonFormatter()
    elif os.getenv("DEBUG", "false").lower() == "true":
        # Detailed format for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
    else:
        # Simple format for other environments (e.g. testing)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Create default logger for application
app_logger = setup_logger("insight_flow")

# Create a default logger for general use
logger = setup_logger("insight_flow")


# ===========================================
# Privacy Utility Functions for Logging
# ===========================================


def mask_email(email: str) -> str:
    """
    Mask email address for privacy in logs.

    Example:
        user@example.com -> u***@e***.com
        john.doe@company.org -> j***@c***.org

    Args:
        email: The email address to mask

    Returns:
        Masked email string
    """
    if not email or "@" not in email:
        return "***"

    try:
        local_part, domain = email.rsplit("@", 1)

        # Mask local part (keep first char)
        masked_local = f"{local_part[0]}***" if len(local_part) > 1 else "***"

        # Mask domain (keep first char and TLD)
        if "." in domain:
            domain_name, tld = domain.rsplit(".", 1)
            masked_domain = f"{domain_name[0]}***.{tld}" if len(domain_name) > 1 else f"***.{tld}"
        else:
            masked_domain = "***"

        return f"{masked_local}@{masked_domain}"
    except Exception:
        return "***@***.***"


def mask_user_id(user_id: str | object) -> str:
    """
    Mask user ID for privacy in logs.

    Example:
        12345678-1234-1234-1234-123456789012 -> 1234****-****-****-****-********9012

    Args:
        user_id: The user ID to mask (str or UUID)

    Returns:
        Masked user ID string
    """
    if not user_id:
        return "***"

    user_id_str = str(user_id)

    if len(user_id_str) <= 8:
        return f"{user_id_str[:2]}***"

    # Keep first 4 and last 4 characters
    return f"{user_id_str[:4]}***{user_id_str[-4:]}"


def mask_token(token: str) -> str:
    """
    Mask token for security in logs.

    Example:
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... -> eyJh***...J9

    Args:
        token: The token to mask

    Returns:
        Masked token string
    """
    if not token:
        return "***"

    if len(token) <= 10:
        return "***"

    return f"{token[:4]}***{token[-4:]}"
