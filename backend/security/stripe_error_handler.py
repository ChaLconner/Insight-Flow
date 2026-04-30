"""
Stripe Error Handler - Safe error message mapping.
Prevents internal error details from being exposed to users.
"""

import logging
from enum import StrEnum

from stripe import (
    APIConnectionError,
    AuthenticationError,
    CardError,
    InvalidRequestError,
    RateLimitError,
    StripeError,
)

logger = logging.getLogger("payment.errors")


class StripeErrorCode(StrEnum):
    """Common Stripe error codes for mapping."""

    CARD_DECLINED = "card_declined"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    EXPIRED_CARD = "expired_card"
    INCORRECT_CVC = "incorrect_cvc"
    INCORRECT_NUMBER = "incorrect_number"
    INVALID_EXPIRY_MONTH = "invalid_expiry_month"
    INVALID_EXPIRY_YEAR = "invalid_expiry_year"
    PROCESSING_ERROR = "processing_error"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION_REQUIRED = "authentication_required"
    PAYMENT_METHOD_NOT_ATTACHED = "payment_method_not_attached"
    CUSTOMER_NOT_FOUND = "resource_missing"
    INVALID_API_KEY = "api_key_expired"


# User-friendly error messages mapped from Stripe error codes
SAFE_ERROR_MESSAGES = {
    # Card errors
    "card_declined": "Your card was declined. Please try a different payment method.",
    "insufficient_funds": "Your card has insufficient funds. Please try another card.",
    "expired_card": "Your card has expired. Please update your card information.",
    "incorrect_cvc": "The security code (CVC) is incorrect. Please check and try again.",
    "incorrect_number": "The card number is incorrect. Please check and try again.",
    "invalid_expiry_month": "The expiration month is invalid. Please check and try again.",
    "invalid_expiry_year": "The expiration year is invalid. Please check and try again.",
    "processing_error": "An error occurred while processing your card. Please try again.",
    # Authentication errors
    "authentication_required": "Additional authentication is required. Please complete the verification.",
    # Rate limiting
    "rate_limit": "Too many requests. Please wait a moment and try again.",
    # Resource errors
    "resource_missing": "The requested resource was not found. Please refresh and try again.",
    "payment_method_not_attached": "This payment method is not available. Please add a new card.",
    # API errors (generic for security)
    "api_key_expired": "Payment service configuration error. Please contact support.",
    "invalid_request_error": "Invalid request. Please check your information and try again.",
    # Generic fallbacks
    "default": "An unexpected error occurred. Please try again or contact support.",
}

# Decline codes have more specific messages
DECLINE_CODE_MESSAGES = {
    "generic_decline": "Your card was declined. Please contact your bank or try another card.",
    "insufficient_funds": "Insufficient funds. Please try another payment method.",
    "lost_card": "This card has been reported lost. Please use a different card.",
    "stolen_card": "This card has been reported stolen. Please use a different card.",
    "fraudulent": "This payment was flagged as potentially fraudulent. Please contact your bank.",
    "do_not_honor": "Your bank declined the payment. Please contact your bank or try another card.",
    "try_again_later": "The payment could not be processed. Please try again later.",
    "not_permitted": "This type of payment is not permitted. Please try another card.",
    "restricted_card": "This card is restricted. Please try another card.",
    "withdrawal_count_limit_exceeded": "You've exceeded your withdrawal limit. Please try again tomorrow.",
}


def get_safe_error_message(error: Exception, include_code: bool = False) -> str:  # noqa: PLR0912
    """
    Convert a Stripe exception to a user-friendly error message.

    Args:
        error: The exception raised by Stripe SDK or internal code
        include_code: Whether to include error code in message (for debugging)

    Returns:
        A safe, user-friendly error message
    """
    error_code = None
    decline_code = None

    if isinstance(error, CardError):
        error_code = error.code
        decline_code = getattr(error, "decline_code", None)

        # Try decline code first (more specific)
        if decline_code and decline_code in DECLINE_CODE_MESSAGES:
            message = DECLINE_CODE_MESSAGES[decline_code]
        elif error_code and error_code in SAFE_ERROR_MESSAGES:
            message = SAFE_ERROR_MESSAGES[error_code]
        else:
            message = SAFE_ERROR_MESSAGES["card_declined"]

    elif isinstance(error, RateLimitError):
        message = SAFE_ERROR_MESSAGES["rate_limit"]
        error_code = "rate_limit"

    elif isinstance(error, InvalidRequestError):
        error_code = getattr(error, "code", "invalid_request_error")

        # Check for specific known patterns
        error_str = str(error).lower()
        if "no such customer" in error_str:
            message = "Your payment profile needs to be refreshed. Please try again."
        elif "no such payment_method" in error_str:
            message = "This payment method is no longer available. Please add a new card."
        elif "no such subscription" in error_str:
            message = "Subscription not found. Please refresh and try again."
        elif error_code in SAFE_ERROR_MESSAGES:
            message = SAFE_ERROR_MESSAGES[error_code]
        else:
            message = SAFE_ERROR_MESSAGES["invalid_request_error"]

    elif isinstance(error, AuthenticationError):
        # Log internally but don't expose API key issues
        logger.critical(f"Stripe authentication error: {error}")
        message = "Payment service is temporarily unavailable. Please try again later."
        error_code = "auth_error"

    elif isinstance(error, APIConnectionError):
        message = (
            "Unable to connect to payment service. Please check your connection and try again."
        )
        error_code = "connection_error"

    elif isinstance(error, StripeError):
        # Generic Stripe error
        error_code = getattr(error, "code", "stripe_error")
        message = SAFE_ERROR_MESSAGES.get(str(error_code), SAFE_ERROR_MESSAGES["default"])

    elif isinstance(error, ValueError):
        # Internal validation errors - these are usually safe to show
        message = str(error)
        error_code = "validation_error"

    else:
        # Unknown error - use generic message
        logger.error(f"Unknown payment error type: {type(error).__name__}: {error}")
        message = SAFE_ERROR_MESSAGES["default"]
        error_code = "unknown_error"

    if include_code and error_code:
        return f"{message} (Error code: {error_code})"

    return message


def parse_stripe_error(error: Exception) -> tuple[str, str, str | None]:
    """
    Parse a Stripe error into components.

    Returns:
        Tuple of (safe_message, error_code, original_message)
    """
    safe_message = get_safe_error_message(error)

    if isinstance(error, StripeError):
        error_code = getattr(error, "code", "unknown")
        original_message = str(error)
    else:
        error_code = type(error).__name__
        original_message = str(error)

    return safe_message, error_code, original_message


def log_and_get_safe_error(error: Exception, operation: str, user_id: str | None = None) -> str:
    """
    Log the full error details internally and return a safe message for the user.

    Args:
        error: The exception
        operation: Name of the operation (e.g., "add_payment_method")
        user_id: Optional user ID for context

    Returns:
        Safe error message for the user
    """
    safe_message, error_code, original_message = parse_stripe_error(error)

    # Log full details internally
    logger.error(
        f"Payment error during {operation}",
        extra={
            "user_id": user_id,
            "operation": operation,
            "error_code": error_code,
            "error_type": type(error).__name__,
            "original_message": original_message,
            "safe_message": safe_message,
        },
    )

    return safe_message
