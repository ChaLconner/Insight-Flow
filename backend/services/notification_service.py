"""
Notification service layer for notification management.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.notification import Notification
from schemas.notification import NotificationCreate
import uuid

class NotificationService:
    """Service class for notification operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_notifications(
        self, 
        user_id: uuid.UUID, 
        skip: int = 0, 
        limit: int = 100, 
        unread_only: bool = False
    ) -> List[Notification]:
        """Get notifications for a user with pagination."""
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        return query.offset(skip).limit(limit).all()
    
    def create_notification(self, notification_data: NotificationCreate) -> Notification:
        """Create a new notification."""
        try:
            db_notification = Notification(
                user_id=notification_data.user_id,
                type=notification_data.type,
                title=notification_data.title,
                message=notification_data.message,
                data=notification_data.data
            )
            
            self.db.add(db_notification)
            self.db.commit()
            self.db.refresh(db_notification)
            return db_notification
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Notification creation failed")
    
    def mark_notification_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Mark a notification as read."""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if not notification:
            raise ValueError("Notification not found")
        
        if notification.is_read:
            return True  # Already read
        
        try:
            notification.is_read = True
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Failed to mark notification as read")
    
    def mark_all_notifications_read(self, user_id: uuid.UUID) -> bool:
        """Mark all notifications as read for a user."""
        try:
            self.db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False
            ).update({"is_read": True})
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Failed to mark all notifications as read")