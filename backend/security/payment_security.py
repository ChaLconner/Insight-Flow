"""
Security utilities for payment operations.
Provides logging, audit trails, and security checks.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request

logger = logging.getLogger("payment.security")


class PaymentSecurityLogger:
    """
    Security logger for payment operations.
    Logs all sensitive payment operations for audit purposes.
    """

    @staticmethod
    def log_payment_operation(
        operation: str,
        user_id: UUID,
        success: bool,
        details: dict | None = None,
        request: Request | None = None,
    ):
        """
        Log a payment operation for audit purposes.

        Args:
            operation: Type of operation (e.g., 'add_card', 'delete_card', 'subscribe')
            user_id: User performing the operation
            success: Whether operation succeeded
            details: Additional details to log
            request: FastAPI request for extracting IP, user agent
        """
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "operation": operation,
            "user_id": str(user_id),
            "success": success,
            "details": details or {},
        }

        # Extract request info if available
        if request:
            log_data["ip_address"] = _get_client_ip(request)
            log_data["user_agent"] = request.headers.get("user-agent", "unknown")

        # Log based on success/failure
        if success:
            logger.info(f"PAYMENT_OP_SUCCESS: {operation}", extra=log_data)
        else:
            logger.warning(f"PAYMENT_OP_FAILED: {operation}", extra=log_data)

        return log_data

    @staticmethod
    def log_suspicious_activity(
        activity_type: str, user_id: UUID | None, request: Request, details: dict
    ):
        """
        Log suspicious payment activity.

        Args:
            activity_type: Type of suspicious activity
            user_id: User if authenticated
            request: FastAPI request
            details: Details of suspicious activity
        """
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "activity_type": activity_type,
            "user_id": str(user_id) if user_id else None,
            "ip_address": _get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "unknown"),
            "details": details,
        }

        logger.warning(f"SUSPICIOUS_ACTIVITY: {activity_type}", extra=log_data)
        return log_data


def _get_client_ip(request: Request) -> str:
    """
    Extract real client IP securely, handling proxies with validation.

    Uses the centralized request_security utility for proper trusted proxy handling.
    """
    from utils.request_security import get_client_ip

    return get_client_ip(request)


def validate_payment_amount(amount: float, currency: str = "usd") -> tuple[bool, str]:
    """
    Validate payment amount for sanity checks.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if amount < 0:
        return False, "Amount cannot be negative"

    if amount > 100000:  # $100,000 limit for safety
        return False, "Amount exceeds maximum allowed"

    # Check for currency-specific minimums (Stripe requirements)
    min_amounts = {
        "usd": 0.50,
        "eur": 0.50,
        "gbp": 0.30,
        "jpy": 50,
    }

    min_amount = min_amounts.get(currency.lower(), 0.50)
    if 0 < amount < min_amount:
        return False, f"Amount is below minimum for {currency.upper()}: {min_amount}"

    return True, ""


def mask_card_number(card_number: str) -> str:
    """
    Mask a card number for safe logging.
    Only shows last 4 digits.
    """
    if not card_number or len(card_number) < 4:
        return "****"
    return "*" * (len(card_number) - 4) + card_number[-4:]


def is_valid_stripe_id(stripe_id: str, prefix: str) -> bool:
    """
    Validate Stripe ID format.

    Args:
        stripe_id: The ID to validate
        prefix: Expected prefix (e.g., 'pm_', 'cus_', 'sub_')

    Returns:
        True if valid format
    """
    if not stripe_id or not isinstance(stripe_id, str):
        return False

    if not stripe_id.startswith(prefix):
        return False

    # Stripe IDs are typically alphanumeric + underscore, 14+ chars
    return len(stripe_id) >= len(prefix) + 10


# Convenience instances
security_logger = PaymentSecurityLogger()
