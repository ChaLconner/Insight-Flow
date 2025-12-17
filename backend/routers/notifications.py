from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from routers.auth import get_current_active_user
from models.notification import Notification
from models.user import User
from schemas.notification import NotificationResponse

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all notifications for the current user.
    """
    notifications = db.query(Notification)\
        .filter(Notification.user_id == current_user.id)\
        .order_by(Notification.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    # Convert to response format to handle schema properly
    result = []
    for notif in notifications:
        result.append(NotificationResponse(
            id=notif.id,
            user_id=notif.user_id,
            type=notif.type,
            title=notif.title,
            message=notif.message,
            data=notif.data,
            is_read=notif.is_read,
            created_at=notif.created_at
        ))
    return result

@router.get("/unread-count", response_model=int)
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get count of unread notifications.
    """
    count = db.query(Notification)\
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)\
        .count()
    return count

@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark a notification as read.
    """
    try:
        notif_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    notification = db.query(Notification)\
        .filter(Notification.id == notif_uuid, Notification.user_id == current_user.id)\
        .first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    
    # Convert to response format to handle schema properly
    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        data=notification.data,
        is_read=notification.is_read,
        created_at=notification.created_at
    )

@router.put("/read-all", response_model=List[NotificationResponse])
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark all notifications as read.
    """
    notifications = db.query(Notification)\
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)\
        .all()
    
    for notification in notifications:
        notification.is_read = True
    
    db.commit()
    
    # Return updated list (recent 50)
    updated_notifications = db.query(Notification)\
        .filter(Notification.user_id == current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(50)\
        .all()
    
    # Convert to response format to handle schema properly
    result = []
    for notif in updated_notifications:
        result.append(NotificationResponse(
            id=notif.id,
            user_id=notif.user_id,
            type=notif.type,
            title=notif.title,
            message=notif.message,
            data=notif.data,
            is_read=notif.is_read,
            created_at=notif.created_at
        ))
    return result

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a notification.
    """
    try:
        notif_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    notification = db.query(Notification)\
        .filter(Notification.id == notif_uuid, Notification.user_id == current_user.id)\
        .first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()

@router.post("/check-deadlines")
async def check_deadlines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually trigger deadline check for due and overdue tasks.
    This can also be called by a cron job/scheduler.
    Returns summary of notifications sent.
    """
    from services.deadline_reminder import run_deadline_check
    
    # Only allow admins to trigger this in production
    # For now, any authenticated user can trigger it
    summary = run_deadline_check(db)
    
    return {
        "message": "Deadline check completed",
        "summary": summary
    }

@router.post("/create-test")
async def create_test_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create sample notifications for testing.
    Creates various types of notifications for the current user.
    """
    test_notifications = [
        {
            "type": "task_assigned",
            "title": "New Task Assigned",
            "message": "John assigned you: Fix login bug",
            "data": {"task_id": "test-123", "project_name": "Insight-Flow"}
        },
        {
            "type": "project_invitation",
            "title": "Added to Project",
            "message": "Sarah added you to Project Alpha",
            "data": {"project_id": "test-456", "project_name": "Project Alpha"}
        },
        {
            "type": "task_due_soon",
            "title": "Task Due Tomorrow",
            "message": "'Design UI' is due tomorrow",
            "data": {"task_id": "test-789", "days_left": 1}
        },
        {
            "type": "task_overdue",
            "title": "Task Overdue",
            "message": "'API Integration' is 2 days overdue",
            "data": {"task_id": "test-101", "days_overdue": 2}
        },
        {
            "type": "task_completed",
            "title": "Task Completed",
            "message": "Mike completed: Database optimization",
            "data": {"task_id": "test-202", "project_name": "Backend"}
        },
    ]
    
    created = []
    for notif_data in test_notifications:
        notification = Notification(
            user_id=current_user.id,
            type=notif_data["type"],
            title=notif_data["title"],
            message=notif_data["message"],
            data=notif_data["data"],
            is_read=False
        )
        db.add(notification)
        created.append(notif_data["title"])
    
    db.commit()
    
    return {
        "message": f"Created {len(created)} test notifications",
        "notifications": created
    }
