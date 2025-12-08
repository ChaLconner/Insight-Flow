"""
Unit tests for NotificationService.
"""
import pytest
import uuid
from models.notification import Notification
from services.notification_service import NotificationService
from schemas.notification import NotificationCreate


class TestNotificationService:
    """Test cases for NotificationService."""

    @pytest.fixture
    def notification_service(self, db_session):
        """Create NotificationService instance."""
        return NotificationService(db_session)

    def test_create_notification_success(self, db_session, test_user, notification_service):
        """Test successful notification creation."""
        notification_data = NotificationCreate(
            user_id=test_user.id,
            type="task_assigned",
            title="New Task Assigned",
            message="You have been assigned a new task"
        )
        
        notification = notification_service.create_notification(notification_data)
        
        assert notification is not None
        assert notification.user_id == test_user.id
        assert notification.type == "task_assigned"
        assert notification.title == "New Task Assigned"
        assert notification.is_read is False

    def test_create_notification_with_data(self, db_session, test_user, notification_service):
        """Test notification creation with additional data."""
        notification_data = NotificationCreate(
            user_id=test_user.id,
            type="project_update",
            title="Project Updated",
            message="Project status changed",
            data={"project_id": str(uuid.uuid4()), "status": "completed"}
        )
        
        notification = notification_service.create_notification(notification_data)
        
        assert notification.data is not None
        assert "project_id" in notification.data

    def test_get_user_notifications(self, db_session, test_user, notification_service):
        """Test getting user notifications."""
        # Create multiple notifications
        for i in range(5):
            notification_data = NotificationCreate(
                user_id=test_user.id,
                type="info",
                title=f"Notification {i}",
                message=f"Message {i}"
            )
            notification_service.create_notification(notification_data)
        
        notifications = notification_service.get_user_notifications(test_user.id)
        
        assert len(notifications) == 5

    def test_get_user_notifications_pagination(self, db_session, test_user, notification_service):
        """Test notification pagination."""
        # Create 5 notifications
        for i in range(5):
            notification_data = NotificationCreate(
                user_id=test_user.id,
                type="info",
                title=f"Notification {i}",
                message=f"Message {i}"
            )
            notification_service.create_notification(notification_data)
        
        # Get first page
        notifications = notification_service.get_user_notifications(test_user.id, skip=0, limit=3)
        assert len(notifications) == 3
        
        # Get second page
        notifications = notification_service.get_user_notifications(test_user.id, skip=3, limit=3)
        assert len(notifications) == 2

    def test_get_user_notifications_unread_only(self, db_session, test_user, notification_service):
        """Test getting unread notifications only."""
        # Create 3 notifications
        notifications_created = []
        for i in range(3):
            notification_data = NotificationCreate(
                user_id=test_user.id,
                type="info",
                title=f"Notification {i}",
                message=f"Message {i}"
            )
            notif = notification_service.create_notification(notification_data)
            notifications_created.append(notif)
        
        # Mark one as read
        notification_service.mark_notification_read(notifications_created[0].id, test_user.id)
        
        # Get unread only
        unread = notification_service.get_user_notifications(test_user.id, unread_only=True)
        assert len(unread) == 2

    def test_mark_notification_read(self, db_session, test_user, notification_service):
        """Test marking notification as read."""
        notification_data = NotificationCreate(
            user_id=test_user.id,
            type="info",
            title="Read This",
            message="Please read"
        )
        notification = notification_service.create_notification(notification_data)
        assert notification.is_read is False
        
        result = notification_service.mark_notification_read(notification.id, test_user.id)
        
        assert result is True
        
        # Verify it's marked as read
        db_session.refresh(notification)
        assert notification.is_read is True

    def test_mark_notification_read_already_read(self, db_session, test_user, notification_service):
        """Test marking already-read notification."""
        notification_data = NotificationCreate(
            user_id=test_user.id,
            type="info",
            title="Already Read",
            message="Already read notification"
        )
        notification = notification_service.create_notification(notification_data)
        
        # Mark as read twice
        notification_service.mark_notification_read(notification.id, test_user.id)
        result = notification_service.mark_notification_read(notification.id, test_user.id)
        
        assert result is True  # Should still return True

    def test_mark_notification_read_not_found(self, db_session, test_user, notification_service):
        """Test marking non-existent notification as read."""
        fake_id = uuid.uuid4()
        
        with pytest.raises(ValueError, match="not found"):
            notification_service.mark_notification_read(fake_id, test_user.id)

    def test_mark_notification_read_wrong_user(self, db_session, test_user, notification_service):
        """Test marking notification as read by wrong user."""
        notification_data = NotificationCreate(
            user_id=test_user.id,
            type="info",
            title="Private",
            message="Private notification"
        )
        notification = notification_service.create_notification(notification_data)
        
        # Try to mark as read by different user
        other_user_id = uuid.uuid4()
        
        with pytest.raises(ValueError, match="not found"):
            notification_service.mark_notification_read(notification.id, other_user_id)

    def test_mark_all_notifications_read(self, db_session, test_user, notification_service):
        """Test marking all notifications as read."""
        # Create multiple unread notifications
        for i in range(5):
            notification_data = NotificationCreate(
                user_id=test_user.id,
                type="info",
                title=f"Notification {i}",
                message=f"Message {i}"
            )
            notification_service.create_notification(notification_data)
        
        result = notification_service.mark_all_notifications_read(test_user.id)
        
        assert result is True
        
        # Verify all are read
        unread = notification_service.get_user_notifications(test_user.id, unread_only=True)
        assert len(unread) == 0

    def test_notifications_isolated_by_user(self, db_session, test_user, notification_service):
        """Test that notifications are isolated by user."""
        from models.user import User
        from utils.auth import get_password_hash
        
        # Create another user
        other_user = User(
            email="other@example.com",
            hashed_password=get_password_hash("password123"),
            name="Other User",
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Create notification for test_user
        notification_data = NotificationCreate(
            user_id=test_user.id,
            type="info",
            title="For Test User",
            message="This is for test user"
        )
        notification_service.create_notification(notification_data)
        
        # Create notification for other_user
        notification_data = NotificationCreate(
            user_id=other_user.id,
            type="info",
            title="For Other User",
            message="This is for other user"
        )
        notification_service.create_notification(notification_data)
        
        # Each user should only see their own notifications
        test_user_notifications = notification_service.get_user_notifications(test_user.id)
        other_user_notifications = notification_service.get_user_notifications(other_user.id)
        
        assert len(test_user_notifications) == 1
        assert len(other_user_notifications) == 1
        assert test_user_notifications[0].title == "For Test User"
        assert other_user_notifications[0].title == "For Other User"
