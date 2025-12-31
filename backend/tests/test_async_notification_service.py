
import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from services.async_notification_service import AsyncNotificationService
from models.notification import Notification, NotificationType
from schemas.notification import NotificationCreate

@pytest.fixture
def mock_db_session():
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    return db

@pytest.fixture
def notification_service(mock_db_session):
    return AsyncNotificationService(mock_db_session)

@pytest.mark.asyncio
async def test_create_notification(notification_service, mock_db_session):
    data = NotificationCreate(
        user_id=uuid.uuid4(),
        type=NotificationType.TASK_ASSIGNED,
        title="Valid Title",
        message="Valid Message",
        data={}
    )
    
    # Mock Notification class creation within service is hard without patching model init or verify helper method.
    # But since arguments are passed to constructor, we can trust sqlalchemy model unit tests.
    
    notification = await notification_service.create_notification(data)
    
    assert notification.title == "Valid Title"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_notifications(notification_service, mock_db_session):
    uid = uuid.uuid4()
    
    res = MagicMock()
    res.scalars.return_value.all.return_value = [Notification(id=uuid.uuid4())]
    mock_db_session.execute.return_value = res
    
    items = await notification_service.get_user_notifications(uid, unread_only=True)
    
    assert len(items) == 1
    mock_db_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_unread_count(notification_service, mock_db_session):
    uid = uuid.uuid4()
    
    res = MagicMock()
    res.scalar.return_value = 5
    mock_db_session.execute.return_value = res
    
    count = await notification_service.get_unread_count(uid)
    
    assert count == 5

@pytest.mark.asyncio
async def test_mark_notification_read_success(notification_service, mock_db_session):
    nid = uuid.uuid4()
    uid = uuid.uuid4()
    
    notification = Notification(id=nid, user_id=uid, is_read=False)
    
    res = MagicMock()
    res.scalar_one_or_none.return_value = notification
    mock_db_session.execute.return_value = res
    
    updated = await notification_service.mark_notification_read(nid, uid)
    
    assert updated.is_read is True
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_mark_notification_read_not_found(notification_service, mock_db_session):
    nid = uuid.uuid4()
    uid = uuid.uuid4()
    
    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = res
    
    with pytest.raises(ValueError, match="not found"):
        await notification_service.mark_notification_read(nid, uid)

@pytest.mark.asyncio
async def test_mark_all_notifications_read(notification_service, mock_db_session):
    uid = uuid.uuid4()
    
    res = MagicMock()
    res.rowcount = 10
    mock_db_session.execute.return_value = res
    
    count = await notification_service.mark_all_notifications_read(uid)
    
    assert count == 10
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_delete_notification(notification_service, mock_db_session):
    nid = uuid.uuid4()
    uid = uuid.uuid4()
    
    notification = Notification(id=nid, user_id=uid)
    
    res = MagicMock()
    res.scalar_one_or_none.return_value = notification
    mock_db_session.execute.return_value = res
    
    result = await notification_service.delete_notification(nid, uid)
    
    assert result is True
    # Verify two execute calls: one for select, one for delete
    assert mock_db_session.execute.call_count == 2
    mock_db_session.commit.assert_called_once()
