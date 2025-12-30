"""
Async notification service layer for notification management.
Replaces the sync NotificationService.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import Notification
from schemas.notification import NotificationCreate


class AsyncNotificationService:
    """Async service class for notification operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_notifications(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100, unread_only: bool = False
    ) -> list[Notification]:
        """Get notifications for a user with pagination."""
        query = select(Notification).filter(Notification.user_id == user_id)

        if unread_only:
            query = query.filter(Notification.is_read == False)

        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get count of unread notifications for a user."""
        from sqlalchemy import func

        query = (
            select(func.count())
            .select_from(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def create_notification(self, notification_data: NotificationCreate) -> Notification:
        """Create a new notification."""
        try:
            db_notification = Notification(
                user_id=notification_data.user_id,
                type=notification_data.type,
                title=notification_data.title,
                message=notification_data.message,
                data=notification_data.data,
            )

            self.db.add(db_notification)
            await self.db.commit()
            await self.db.refresh(db_notification)
            return db_notification

        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Notification creation failed")

    async def mark_notification_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification:
        """Mark a notification as read."""
        result = await self.db.execute(
            select(Notification).filter(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            raise ValueError("Notification not found")

        if notification.is_read:
            return notification  # Already read

        try:
            notification.is_read = True
            await self.db.commit()
            await self.db.refresh(notification)
            return notification
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Failed to mark notification as read")

    async def mark_all_notifications_read(self, user_id: uuid.UUID) -> int:
        """Mark all notifications as read for a user. Returns count updated."""
        try:
            result = await self.db.execute(
                update(Notification)
                .where(Notification.user_id == user_id, Notification.is_read == False)
                .values(is_read=True)
            )
            await self.db.commit()
            return result.rowcount  # type: ignore
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Failed to mark all notifications as read")

    async def delete_notification(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a notification."""
        from sqlalchemy import delete

        result = await self.db.execute(
            select(Notification).filter(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            raise ValueError("Notification not found")

        await self.db.execute(delete(Notification).where(Notification.id == notification_id))
        await self.db.commit()
        return True
