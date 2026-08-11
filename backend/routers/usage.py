from typing import Annotated

from fastapi import APIRouter, Depends

from dependencies.auth import get_current_user
from dependencies.services import get_usage_service
from models import User
from services.async_usage_service import AsyncUsageService

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/stats")
async def get_usage_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    usage_service: Annotated[AsyncUsageService, Depends(get_usage_service)],
):
    """
    Get usage statistics for the current user.
    Returns:
    - projects_used: Number of projects owned or member of
    - storage_used_bytes: Total size of uploaded files in bytes
    - seats_used: Number of unique members in projects owned by the user (including self)
    """
    return await usage_service.get_user_usage_stats(current_user)
