"""
Notification Management router - handles fetching and managing user notifications.
Refactored to use AsyncNotificationService and Dependency Injection.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from dependencies.services import get_async_notification_service
from models.user import User
from routers.auth import get_current_active_user
from schemas.notification import NotificationResponse
from services.async_deadline_reminder import run_async_deadline_check
from services.async_notification_service import AsyncNotificationService
from utils.logger import mask_user_id, setup_logger
from utils.response_helpers import build_notification_response

logger = setup_logger("notifications_router")

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    notification_service: AsyncNotificationService = Depends(get_async_notification_service),
    current_user: User = Depends(get_current_active_user),
) -> list[NotificationResponse]:
    """Get notifications for the current user."""
    notifications = await notification_service.get_user_notifications(
        current_user.id, skip=skip, limit=limit, unread_only=unread_only
    )
    return [
        NotificationResponse.model_validate(build_notification_response(n)) for n in notifications
    ]


@router.get("/unread-count", response_model=int)
async def get_unread_count(
    notification_service: AsyncNotificationService = Depends(get_async_notification_service),
    current_user: User = Depends(get_current_active_user),
) -> int:
    """Get count of unread notifications."""
    return await notification_service.get_unread_count(current_user.id)


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    notification_service: AsyncNotificationService = Depends(get_async_notification_service),
    current_user: User = Depends(get_current_active_user),
) -> NotificationResponse:
    """Mark a notification as read."""
    try:
        notif_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID"
        )

    try:
        notification = await notification_service.mark_notification_read(
            notif_uuid, current_user.id
        )
        logger.info(
            f"Notification {notification.id} marked as read by user {mask_user_id(current_user.id)}"
        )
        return NotificationResponse.model_validate(build_notification_response(notification))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/read-all", response_model=dict)
async def mark_all_read(
    notification_service: AsyncNotificationService = Depends(get_async_notification_service),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Mark all notifications as read."""
    count = await notification_service.mark_all_notifications_read(current_user.id)
    logger.info(
        f"All notifications ({count}) marked as read for user {mask_user_id(current_user.id)}"
    )
    return {"message": "All notifications marked as read", "count": count}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    notification_service: AsyncNotificationService = Depends(get_async_notification_service),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a notification."""
    try:
        notif_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID"
        )

    try:
        await notification_service.delete_notification(notif_uuid, current_user.id)
        logger.info(f"Notification {notif_uuid} deleted by user {mask_user_id(current_user.id)}")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/check-deadlines")
async def check_deadlines(
    db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_active_user)
) -> dict:
    """Manually trigger deadline check for due and overdue tasks."""
    summary = await run_async_deadline_check(db)
    return {"message": "Deadline check completed", "summary": summary}


@router.post("/create-test")
async def create_test_notifications(
    notification_service: AsyncNotificationService = Depends(get_async_notification_service),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Create sample notifications for testing."""
    from schemas.notification import NotificationCreate

    test_notifications = [
        {
            "type": "task_assigned",
            "title": "New Task Assigned",
            "message": "John assigned you: Fix login bug",
        },
        {
            "type": "project_invitation",
            "title": "Added to Project",
            "message": "Sarah added you to Project Alpha",
        },
        {
            "type": "task_due_soon",
            "title": "Task Due Tomorrow",
            "message": "'Design UI' is due tomorrow",
        },
    ]

    created_titles = []
    for data in test_notifications:
        notif_create = NotificationCreate(
            user_id=current_user.id,
            type=data["type"],
            title=data["title"],
            message=data["message"],
            data={"test": True},
        )
        await notification_service.create_notification(notif_create)
        created_titles.append(data["title"])

    return {
        "message": f"Created {len(created_titles)} test notifications",
        "notifications": created_titles,
    }
