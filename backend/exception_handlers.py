import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import get_settings
from utils.exceptions import AppError
from utils.logger import app_logger
from database import AsyncSessionLocal
from services.security_log_service import SecurityLogService


def add_exception_handlers(app: FastAPI):
    """
    Register global exception handlers for the FastAPI application.

    Security Note: All handlers are designed to prevent information leakage
    by returning generic error messages in production while logging full
    details internally for debugging.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        Standardize HTTP exceptions to match API response format.
        """
        if exc.status_code == 403:
            try:
                # Log audit event for 403 Forbidden
                async with AsyncSessionLocal() as db:
                    await SecurityLogService.log_event(
                        db=db,
                        event_type="access_denied",
                        severity="warning",
                        details={"detail": str(exc.detail)},
                        request=request,
                    )
            except Exception as e:
                app_logger.error(f"Failed to log 403 error: {e}")

        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": str(exc.detail), "code": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Standardize validation errors.
        Security: Only expose field names, not internal details.
        """
        # Get the first error message for the main message
        error_msg = "Validation Error"
        formatted_errors = []

        if exc.errors():
            try:
                # Try to get a clean error message
                e = exc.errors()[0]
                if "msg" in e:
                    error_msg = e["msg"]
                if "loc" in e:
                    # Only show field path, not internal details
                    error_msg += f" in {' -> '.join(str(loc) for loc in e['loc'])}"

                # Format errors to be JSON serializable and secure
                for e in exc.errors():
                    # Create a safe error dict without internal details
                    safe_error = {
                        "loc": e.get("loc"),
                        "msg": e.get("msg"),
                        "type": e.get("type"),
                    }
                    # Explicitly exclude 'ctx', 'url', and other potentially sensitive fields
                    formatted_errors.append(safe_error)

            except Exception as format_error:
                app_logger.error(f"Error formatting validation exception: {format_error}")
                formatted_errors = [{"msg": "Validation failed"}]

        return JSONResponse(
            status_code=422,
            content={"success": False, "message": error_msg, "errors": formatted_errors},
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        """
        Handle standardized AppErrors.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "code": exc.code,
                "details": exc.details,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """
        Handle ValueError exceptions.
        Security: Log full error internally, return safe message to client.
        """
        app_logger.warning(f"ValueError: {exc}")

        # Only return the error message if it's a known safe message
        safe_messages = [
            "User not found",
            "Email already registered",
            "Username already taken",
            "Incorrect current password",
            "Failed to change password",
            "Could not retrieve user settings",
            "Failed to update settings",
            "User creation failed",
            "User update failed",
            "Failed to invite user",
            "Invalid plan",
            "Plan not found",
        ]

        error_message = str(exc)
        # Check if the message starts with any safe message prefix
        is_safe = any(error_message.startswith(safe_msg) for safe_msg in safe_messages)

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": error_message if is_safe else "Invalid request",
                "code": "BAD_REQUEST",
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        """
        Handle database integrity errors.
        Security: Never expose database details to client.
        """
        # Log full error internally for debugging
        app_logger.warning(f"IntegrityError: {exc}")

        # Determine a safe, generic message based on the type of constraint
        msg = "A conflict occurred while processing your request"

        if hasattr(exc, "orig") and exc.orig:
            error_str = str(exc.orig).lower()
            if "unique constraint" in error_str or "duplicate" in error_str:
                msg = "This record already exists"
            elif "foreign key" in error_str:
                msg = "Referenced record not found"
            elif "not null" in error_str:
                msg = "Required field is missing"
            # Note: We intentionally do NOT include the raw error details

        return JSONResponse(
            status_code=409,
            content={"success": False, "message": msg, "code": "CONFLICT"},
            # Security: Removed "detail": str(exc) to prevent information leakage
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Handle all unhandled exceptions.
        Security: Never expose internal errors to client in production.
        """
        error_id = os.urandom(4).hex()

        # Log full error with traceback for internal debugging
        app_logger.error(f"Unhandled exception {error_id}: {exc}", exc_info=True)

        settings = get_settings()

        # Prepare response content
        content = {
            "success": False,
            "message": "An unexpected error occurred. Please try again later.",
            "error_id": error_id,  # Include error ID so users can report issues
        }

        # Only include error details in development (never in production)
        if settings.environment == "development":
            content["detail"] = str(exc)
            content["type"] = type(exc).__name__

        return JSONResponse(
            status_code=500,
            content=content,
        )
