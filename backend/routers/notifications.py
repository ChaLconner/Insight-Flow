"""
Notifications router for managing user notifications.
"""
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from schemas.notification import NotificationResponse, NotificationCreate
from services.notification_service import NotificationService
from database import get_db
from routers.auth import get_current_active_user
from models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    skip: int = 0,
    limit: int = 100,
    unread_only: bool = Query(False, description="Filter to show only unread notifications"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get notifications for the current user.
    """
    notification_service = NotificationService(db)
    notifications = notification_service.get_user_notifications(
        current_user.id, skip=skip, limit=limit, unread_only=unread_only
    )
    return notifications

@router.post("/", response_model=NotificationResponse)
def create_notification(
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new notification.
    """
    notification_service = NotificationService(db)
    
    # Only allow creating notifications for the current user
    if notification_data.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create notifications for other users"
        )
    
    try:
        notification = notification_service.create_notification(notification_data)
        return notification
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Mark a notification as read.
    """
    import uuid
    notification_service = NotificationService(db)
    
    try:
        notification_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid notification ID format"
        )
    
    try:
        notification_service.mark_notification_read(notification_uuid, current_user.id)
        return {"message": "Notification marked as read"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Mark all notifications as read for the current user.
    """
    notification_service = NotificationService(db)
    
    try:
        notification_service.mark_all_notifications_read(current_user.id)
        return {"message": "All notifications marked as read"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )