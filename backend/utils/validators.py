import re
import uuid

from fastapi import HTTPException, status

from models.task import TaskPriority, TaskType


def validate_uuid(id_string: str, detail: str = "Invalid ID format") -> uuid.UUID:
    """
    Validates if a string is a valid UUID.
    Raises HTTPException 422 if invalid.
    """
    try:
        return uuid.UUID(id_string)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def validate_email(email: str) -> str:
    """
    Validates email format using regex.
    """
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid email format"
        )
    return email


def validate_password_strength(password: str) -> str:
    """
    Validates password strength:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    """
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long",
        )

    return password


def validate_status_value(v: str | None) -> str | None:
    """Validate status value."""
    if v is not None:
        valid_statuses = ["todo", "in_progress", "in_review", "done", "cancelled"]
        if v.lower() not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower()
    return None


def validate_priority_value(v: str | None) -> str | None:
    if v:
        try:
            return TaskPriority(v.lower()).value
        except ValueError:
            raise ValueError(
                f"Priority must be one of: {', '.join([e.value for e in TaskPriority])}"
            )
    return None


def validate_type_value(v: str | None) -> str | None:
    if v:
        try:
            return TaskType(v.lower()).value
        except ValueError:
            raise ValueError(f"Type must be one of: {', '.join([e.value for e in TaskType])}")
    return None
