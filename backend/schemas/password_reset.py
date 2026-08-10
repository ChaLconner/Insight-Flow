"""
Password reset schemas for API requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field


class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password."""

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Response schema for forgot password."""

    message: str
    success: bool


class ResetPasswordRequest(BaseModel):
    """Request schema for reset password."""

    token: str = Field(..., max_length=512)
    new_password: str = Field(..., min_length=8, max_length=128)


class ResetPasswordResponse(BaseModel):
    """Response schema for reset password."""

    message: str
    success: bool
