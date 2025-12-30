"""
Standardized error messages for Insight-Flow API.
User-friendly, consistent error messages in English.
"""

from typing import Final


class ErrorMessages:
    """
    Centralized error message constants.
    These messages are user-friendly and suitable for display in the UI.
    """

    # ===================================
    # Authentication Errors
    # ===================================
    AUTH_INVALID_CREDENTIALS: Final[str] = (
        "Invalid email or password. Please check your credentials and try again."
    )
    AUTH_SESSION_EXPIRED: Final[str] = "Your session has expired. Please log in again."
    AUTH_TOKEN_INVALID: Final[str] = "Invalid authentication token. Please log in again."
    AUTH_TOKEN_EXPIRED: Final[str] = "Your access token has expired. Please refresh your session."
    AUTH_ACCOUNT_INACTIVE: Final[str] = "Your account has been deactivated. Please contact support."
    AUTH_ACCOUNT_NOT_VERIFIED: Final[str] = "Please verify your email address before logging in."
    AUTH_REFRESH_TOKEN_INVALID: Final[str] = "Invalid refresh token. Please log in again."
    AUTH_OAUTH_FAILED: Final[str] = (
        "Authentication with external provider failed. Please try again."
    )
    AUTH_PASSWORD_MISMATCH: Final[str] = "The passwords you entered do not match."
    AUTH_PASSWORD_TOO_WEAK: Final[str] = (
        "Password must be at least 8 characters with a mix of letters and numbers."
    )
    AUTH_EMAIL_ALREADY_EXISTS: Final[str] = "An account with this email already exists."
    AUTH_EMAIL_NOT_FOUND: Final[str] = "No account found with this email address."

    # ===================================
    # Authorization/Permission Errors
    # ===================================
    PERMISSION_DENIED: Final[str] = "You don't have permission to perform this action."
    NOT_PROJECT_MEMBER: Final[str] = "You are not a member of this project."
    NOT_PROJECT_OWNER: Final[str] = "Only the project owner can perform this action."
    INSUFFICIENT_ROLE: Final[str] = (
        "Your role does not have sufficient permissions for this action."
    )
    PROJECT_ACCESS_DENIED: Final[str] = "You don't have access to this project."
    TASK_ACCESS_DENIED: Final[str] = "You don't have access to this task."

    # ===================================
    # Resource Not Found Errors
    # ===================================
    USER_NOT_FOUND: Final[str] = "User not found."
    PROJECT_NOT_FOUND: Final[str] = (
        "The project you're looking for doesn't exist or has been deleted."
    )
    TASK_NOT_FOUND: Final[str] = "The task you're looking for doesn't exist or has been deleted."
    FILE_NOT_FOUND: Final[str] = "The file you're looking for doesn't exist or has been deleted."
    NOTIFICATION_NOT_FOUND: Final[str] = "Notification not found."
    SUBSCRIPTION_NOT_FOUND: Final[str] = "Subscription not found."
    MEMBER_NOT_FOUND: Final[str] = "Member not found in this project."

    # ===================================
    # Validation Errors
    # ===================================
    VALIDATION_REQUIRED: Final[str] = "This field is required."
    VALIDATION_INVALID_FORMAT: Final[str] = "The format of this field is invalid."
    VALIDATION_INVALID_EMAIL: Final[str] = "Please enter a valid email address."
    VALIDATION_INVALID_UUID: Final[str] = "Invalid ID format. Please check and try again."
    VALIDATION_TOO_SHORT: Final[str] = "This value is too short."
    VALIDATION_TOO_LONG: Final[str] = "This value is too long."
    VALIDATION_INVALID_DATE: Final[str] = "Please enter a valid date."
    VALIDATION_DATE_IN_PAST: Final[str] = "The date cannot be in the past."
    VALIDATION_INVALID_STATUS: Final[str] = "Invalid status value."
    VALIDATION_INVALID_PRIORITY: Final[str] = "Invalid priority value."

    # ===================================
    # Conflict Errors
    # ===================================
    DUPLICATE_PROJECT_NAME: Final[str] = "A project with this name already exists."
    DUPLICATE_TASK_TITLE: Final[str] = "A task with this title already exists in the project."
    MEMBER_ALREADY_EXISTS: Final[str] = "This user is already a member of the project."
    CANNOT_REMOVE_OWNER: Final[str] = "The project owner cannot be removed from the project."
    CANNOT_DEMOTE_OWNER: Final[str] = "The project owner's role cannot be changed."

    # ===================================
    # Rate Limiting Errors
    # ===================================
    RATE_LIMIT_EXCEEDED: Final[str] = "Too many requests. Please wait a moment and try again."
    RATE_LIMIT_LOGIN: Final[str] = (
        "Too many login attempts. Please wait a few minutes before trying again."
    )
    RATE_LIMIT_API: Final[str] = "API rate limit exceeded. Please slow down your requests."

    # ===================================
    # File Upload Errors
    # ===================================
    FILE_TOO_LARGE: Final[str] = "The file is too large. Maximum file size is {max_size}MB."
    FILE_TYPE_NOT_ALLOWED: Final[str] = (
        "This file type is not allowed. Supported types: {allowed_types}."
    )
    FILE_UPLOAD_FAILED: Final[str] = "File upload failed. Please try again."
    FILE_DELETE_FAILED: Final[str] = "Failed to delete the file. Please try again."
    INVALID_FILE_PATH: Final[str] = "Invalid file path."

    # ===================================
    # Payment/Subscription Errors
    # ===================================
    PAYMENT_FAILED: Final[str] = (
        "Payment processing failed. Please check your payment details and try again."
    )
    PAYMENT_CARD_DECLINED: Final[str] = (
        "Your card was declined. Please try a different payment method."
    )
    PAYMENT_CARD_EXPIRED: Final[str] = "Your card has expired. Please update your payment method."
    SUBSCRIPTION_REQUIRED: Final[str] = (
        "This feature requires a subscription. Please upgrade your plan."
    )
    SUBSCRIPTION_LIMIT_REACHED: Final[str] = (
        "You've reached the limit for your current plan. Please upgrade to continue."
    )
    SUBSCRIPTION_ALREADY_ACTIVE: Final[str] = "You already have an active subscription."
    SUBSCRIPTION_CANCELLED: Final[str] = "Your subscription has been cancelled."

    # ===================================
    # Usage Limit Errors
    # ===================================
    PROJECT_LIMIT_REACHED: Final[str] = (
        "You've reached the maximum number of projects for your plan."
    )
    MEMBER_LIMIT_REACHED: Final[str] = (
        "You've reached the maximum number of team members for your plan."
    )
    STORAGE_LIMIT_REACHED: Final[str] = "You've reached the storage limit for your plan."
    TASK_LIMIT_REACHED: Final[str] = "You've reached the maximum number of tasks for this project."

    # ===================================
    # Server/System Errors
    # ===================================
    INTERNAL_ERROR: Final[str] = "An unexpected error occurred. Please try again later."
    SERVICE_UNAVAILABLE: Final[str] = (
        "The service is temporarily unavailable. Please try again later."
    )
    DATABASE_ERROR: Final[str] = "A database error occurred. Please try again later."
    EXTERNAL_SERVICE_ERROR: Final[str] = (
        "An external service is not responding. Please try again later."
    )
    TIMEOUT_ERROR: Final[str] = "The operation timed out. Please try again."

    # ===================================
    # Generic Messages
    # ===================================
    OPERATION_FAILED: Final[str] = "The operation failed. Please try again."
    INVALID_REQUEST: Final[str] = "Invalid request. Please check your input and try again."
    NOT_IMPLEMENTED: Final[str] = "This feature is not yet available."


class ErrorCodes:
    """
    Standardized error codes for API responses.
    These codes can be used by the frontend for mapping to localized messages.
    """

    # Authentication
    AUTH_INVALID_CREDENTIALS = "AUTH_001"
    AUTH_SESSION_EXPIRED = "AUTH_002"
    AUTH_TOKEN_INVALID = "AUTH_003"
    AUTH_ACCOUNT_INACTIVE = "AUTH_004"
    AUTH_ACCOUNT_NOT_VERIFIED = "AUTH_005"
    AUTH_EMAIL_EXISTS = "AUTH_006"
    AUTH_EMAIL_NOT_FOUND = "AUTH_007"

    # Authorization
    PERMISSION_DENIED = "PERM_001"
    NOT_PROJECT_MEMBER = "PERM_002"
    INSUFFICIENT_ROLE = "PERM_003"

    # Not Found
    USER_NOT_FOUND = "NOT_FOUND_001"
    PROJECT_NOT_FOUND = "NOT_FOUND_002"
    TASK_NOT_FOUND = "NOT_FOUND_003"
    FILE_NOT_FOUND = "NOT_FOUND_004"

    # Validation
    VALIDATION_ERROR = "VALID_001"
    INVALID_FORMAT = "VALID_002"

    # Conflict
    DUPLICATE_RESOURCE = "CONFLICT_001"
    MEMBER_EXISTS = "CONFLICT_002"

    # Rate Limiting
    RATE_LIMITED = "RATE_001"

    # Payment
    PAYMENT_FAILED = "PAY_001"
    SUBSCRIPTION_REQUIRED = "PAY_002"
    LIMIT_REACHED = "PAY_003"

    # Server
    INTERNAL_ERROR = "SYS_001"
    SERVICE_UNAVAILABLE = "SYS_002"
    TIMEOUT = "SYS_003"


def format_error(template: str, **kwargs) -> str:
    """
    Format an error message template with dynamic values.

    Args:
        template: Error message template with {placeholders}
        **kwargs: Values to substitute into the template

    Returns:
        Formatted error message

    Example:
        >>> format_error(ErrorMessages.FILE_TOO_LARGE, max_size=10)
        "The file is too large. Maximum file size is 10MB."
    """
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
