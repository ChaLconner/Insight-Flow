import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import get_settings
from utils.exceptions import AppError
from utils.logger import app_logger


def add_exception_handlers(app: FastAPI):
    """
    Register global exception handlers for the FastAPI application.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        Standardize HTTP exceptions to match API response format.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": str(exc.detail), "code": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Standardize validation errors.
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
                    error_msg += f" in {' -> '.join(str(loc) for loc in e['loc'])}"

                # Format errors to be JSON serializable
                for e in exc.errors():
                    # specific handling for 'ctx' which might contain exception objects
                    error_dict = e.copy()
                    if "ctx" in error_dict and "error" in error_dict["ctx"]:
                        # exceptions are not serializable, convert to str
                        error_dict["ctx"]["error"] = str(error_dict["ctx"]["error"])
                    if "url" in error_dict:
                        error_dict.pop("url")  # URL objects might cause issues too
                    formatted_errors.append(error_dict)

            except Exception as e:
                app_logger.error(f"Error formatting validation exception: {e}")
                formatted_errors = [{"msg": str(exc)}]

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
        app_logger.warning(f"ValueError: {exc}")
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(exc), "code": "BAD_REQUEST"}
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        app_logger.warning(f"IntegrityError: {exc}")
        # Try to extract clearer message
        msg = "Database constraint violation"
        if hasattr(exc, "orig") and str(exc.orig) and "unique constraint" in str(exc.orig).lower():
            msg = "Duplicate entry detected"

        return JSONResponse(
            status_code=409, content={"success": False, "message": msg, "detail": str(exc)}
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_id = os.urandom(4).hex()
        app_logger.error(f"Unhandled exception {error_id}: {exc}", exc_info=True)

        settings = get_settings()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal Server Error",
                "error_id": error_id,
                "detail": str(exc) if settings.environment == "development" else None,
            },
        )
