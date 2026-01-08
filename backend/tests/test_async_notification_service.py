from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from models.notification import Notification
from schemas.notification import NotificationCreate
from services.async_notification_service import AsyncNotificationService


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 0
    session.execute.return_value = mock_result
    return session


@pytest.fixture
def service(mock_db_session):
    return AsyncNotificationService(mock_db_session)


@pytest.mark.asyncio
class TestAsyncNotificationService:
    async def test_get_user_notifications(self, service, mock_db_session):
        user_id = uuid4()
        # Setup mock return
        notif = Notification(id=uuid4(), user_id=user_id, title="Test")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [notif]
        mock_db_session.execute.return_value = mock_result

        result = await service.get_user_notifications(user_id)
        assert len(result) == 1
        assert result[0].title == "Test"

        # Test query construction (indirectly via calls)
        assert mock_db_session.execute.called

    async def test_get_unread_count(self, service, mock_db_session):
        user_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db_session.execute.return_value = mock_result

        count = await service.get_unread_count(user_id)
        assert count == 5

    async def test_create_notification(self, service, mock_db_session):
        data = NotificationCreate(user_id=uuid4(), type="info", title="New", message="Msg")

        created = await service.create_notification(data)
        assert created.title == "New"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()

    async def test_create_notification_error(self, service, mock_db_session):
        mock_db_session.commit.side_effect = IntegrityError("Error", {}, Exception())
        data = NotificationCreate(user_id=uuid4(), type="info", title="t", message="m")

        with pytest.raises(ValueError, match="Notification creation failed"):
            await service.create_notification(data)
        mock_db_session.rollback.assert_awaited_once()

    async def test_mark_notification_read(self, service, mock_db_session):
        notif_id = uuid4()
        user_id = uuid4()

        # Scenario 1: Not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Notification not found"):
            await service.mark_notification_read(notif_id, user_id)

        # Scenario 2: Already read
        notif = Notification(id=notif_id, is_read=True)
        mock_result.scalar_one_or_none.return_value = notif
        result = await service.mark_notification_read(notif_id, user_id)
        assert result.is_read is True
        mock_db_session.commit.assert_not_awaited()

        # Scenario 3: Mark read success
        notif = Notification(id=notif_id, is_read=False)
        mock_result.scalar_one_or_none.return_value = notif
        result = await service.mark_notification_read(notif_id, user_id)
        assert result.is_read is True
        mock_db_session.commit.assert_awaited()

    async def test_mark_notification_read_error(self, service, mock_db_session):
        notif = Notification(id=uuid4(), is_read=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notif
        mock_db_session.execute.return_value = mock_result

        mock_db_session.commit.side_effect = IntegrityError("Error", {}, Exception())

        with pytest.raises(ValueError, match="Failed to mark"):
            await service.mark_notification_read(notif.id, uuid4())
        mock_db_session.rollback.assert_awaited()

    async def test_mark_all_read(self, service, mock_db_session):
        user_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 10
        mock_db_session.execute.return_value = mock_result

        count = await service.mark_all_notifications_read(user_id)
        assert count == 10
        mock_db_session.commit.assert_awaited()

    async def test_mark_all_read_error(self, service, mock_db_session):
        mock_db_session.commit.side_effect = IntegrityError("Error", {}, Exception())
        with pytest.raises(ValueError):
            await service.mark_all_notifications_read(uuid4())
        mock_db_session.rollback.assert_awaited()

    async def test_delete_notification(self, service, mock_db_session):
        notif_id = uuid4()
        # Found
        notif = Notification(id=notif_id)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notif
        mock_db_session.execute.return_value = mock_result

        success = await service.delete_notification(notif_id, uuid4())
        assert success is True
        mock_db_session.commit.assert_awaited()

    async def test_delete_notification_not_found(self, service, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Notification not found"):
            await service.delete_notification(uuid4(), uuid4())
