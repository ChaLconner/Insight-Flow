"""
Password reset schemas for API requests and responses.
"""
from pydantic import BaseModel, EmailStr

class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password."""
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    """Response schema for forgot password."""
    message: str
    success: bool

class ResetPasswordRequest(BaseModel):
    """Request schema for reset password."""
    token: str
    new_password: str

class ResetPasswordResponse(BaseModel):
    """Response schema for reset password."""
    message: str
    success: bool