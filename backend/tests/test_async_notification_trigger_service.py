import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import Notification
from models.user import User
from services.async_notification_trigger_service import AsyncNotificationTriggerService


@pytest.fixture
def mock_db_session():
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def trigger_service(mock_db_session, mock_rate_limiter):
    return AsyncNotificationTriggerService(mock_db_session)


@pytest.fixture
def mock_rate_limiter():
    with patch("services.async_notification_trigger_service.get_rate_limiter") as mock_get:
        limiter = MagicMock()
        limiter.can_send.return_value = (True, "OK")
        mock_get.return_value = limiter
        yield limiter


@pytest.fixture
def users():
    u1 = User(id=uuid.uuid4(), email="u1@test.com", name="User 1")
    u2 = User(id=uuid.uuid4(), email="u2@test.com", name="User 2")
    return u1, u2


@pytest.mark.asyncio
async def test_notify_task_assigned_success(
    trigger_service, mock_db_session, mock_rate_limiter, users
):
    assigner, assignee = users
    task_id = uuid.uuid4()
    project_id = uuid.uuid4()

    # Mock user preferences (empty returns defaults -> True)
    with patch.object(
        trigger_service, "_get_user_preferences", return_value={"inApp": {"tasks": True}}
    ):
        await trigger_service.notify_task_assigned(
            assignee=assignee,
            task_id=task_id,
            task_title="Test Task",
            project_id=project_id,
            project_name="Test Project",
            assigner=assigner,
        )

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        args = mock_db_session.add.call_args[0][0]
        assert isinstance(args, Notification)
        assert args.type == "task_assigned"
        assert args.user_id == assignee.id


@pytest.mark.asyncio
async def test_notify_task_assigned_sends_email_when_enabled(trigger_service, users):
    assigner, assignee = users

    with (
        patch.object(
            trigger_service,
            "_get_user_preferences",
            return_value={"inApp": {"tasks": False}, "email": {"tasks": True}},
        ),
        patch(
            "services.async_notification_trigger_service.EmailService.send_email",
            new_callable=AsyncMock,
        ) as mock_send_email,
    ):
        await trigger_service.notify_task_assigned(
            assignee=assignee,
            task_id=uuid.uuid4(),
            task_title="Test Task",
            project_id=uuid.uuid4(),
            project_name="Test Project",
            assigner=assigner,
        )

        mock_send_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_task_assigned_rate_limited(
    trigger_service, mock_db_session, mock_rate_limiter, users
):
    assigner, assignee = users

    mock_rate_limiter.can_send.return_value = (False, "Limit reached")

    await trigger_service.notify_task_assigned(
        assignee=assignee,
        task_id=uuid.uuid4(),
        task_title="Test Task",
        project_id=uuid.uuid4(),
        project_name="Test Project",
        assigner=assigner,
    )

    # Should skip DB add
    mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_notify_task_assigned_disabled_pref(trigger_service, mock_db_session, users):
    assigner, assignee = users

    with patch.object(
        trigger_service, "_get_user_preferences", return_value={"inApp": {"tasks": False}}
    ):
        await trigger_service.notify_task_assigned(
            assignee=assignee,
            task_id=uuid.uuid4(),
            task_title="Test Task",
            project_id=uuid.uuid4(),
            project_name="Test Project",
            assigner=assigner,
        )

        mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_notify_task_status_changed(trigger_service, mock_db_session, users):
    changer, assignee = users

    with (
        patch.object(
            trigger_service, "_get_user_preferences", return_value={"inApp": {"tasks": True}}
        ),
        patch.object(trigger_service, "_find_existing_group_notification", return_value=None),
    ):
        await trigger_service.notify_task_status_changed(
            task_id=uuid.uuid4(),
            task_title="Test Task",
            project_id=uuid.uuid4(),
            old_status="todo",
            new_status="in_progress",
            changer=changer,
            assignee=assignee,
        )

        mock_db_session.add.assert_called_once()
        args = mock_db_session.add.call_args[0][0]
        assert args.type == "task_updated"


@pytest.mark.asyncio
async def test_notify_task_status_changed_respects_updates_pref(
    trigger_service, mock_db_session, users
):
    changer, assignee = users

    with patch.object(
        trigger_service,
        "_get_user_preferences",
        return_value={"inApp": {"updates": False}, "email": {"tasks": False}},
    ):
        await trigger_service.notify_task_status_changed(
            task_id=uuid.uuid4(),
            task_title="Test Task",
            project_id=uuid.uuid4(),
            old_status="todo",
            new_status="in_progress",
            changer=changer,
            assignee=assignee,
        )

        mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_notify_task_completed(trigger_service, mock_db_session, users):
    completer, creator = users

    with patch.object(
        trigger_service, "_get_user_preferences", return_value={"inApp": {"tasks": True}}
    ):
        await trigger_service.notify_task_completed(
            task_id=uuid.uuid4(),
            task_title="Test Task",
            project_id=uuid.uuid4(),
            project_name="Test Project",
            completer=completer,
            creator=creator,
        )

        mock_db_session.add.assert_called_once()
        args = mock_db_session.add.call_args[0][0]
        assert args.type == "task_completed"


@pytest.mark.asyncio
async def test_notify_project_member_added(trigger_service, mock_db_session, users):
    inviter, new_member = users

    with patch.object(
        trigger_service, "_get_user_preferences", return_value={"inApp": {"projects": True}}
    ):
        await trigger_service.notify_project_member_added(
            new_member=new_member,
            project_id=uuid.uuid4(),
            project_name="New Project",
            role="member",
            inviter=inviter,
        )

        mock_db_session.add.assert_called_once()
        args = mock_db_session.add.call_args[0][0]
        assert args.type == "project_invitation"


@pytest.mark.asyncio
async def test_notify_project_member_removed(trigger_service, mock_db_session, users):
    remover, removed_member = users

    with patch.object(
        trigger_service,
        "_get_user_preferences",
        return_value={"inApp": {"projects": True}, "email": {"projects": False}},
    ):
        await trigger_service.notify_project_member_removed(
            removed_member=removed_member,
            project_id=uuid.uuid4(),
            project_name="Old Project",
            remover=remover,
        )

        mock_db_session.add.assert_called_once()
        args = mock_db_session.add.call_args[0][0]
        assert args.type == "project_member_left"


@pytest.mark.asyncio
async def test_notify_mention_respects_mentions_pref(trigger_service, mock_db_session, users):
    actor, mentioned_user = users

    with patch.object(
        trigger_service,
        "_get_user_preferences",
        return_value={"inApp": {"mentions": True}, "email": {"mentions": False}},
    ):
        await trigger_service.notify_mention(
            mentioned_user=mentioned_user,
            actor=actor,
            message="Please review this",
            project_id=uuid.uuid4(),
        )

        mock_db_session.add.assert_called_once()
        args = mock_db_session.add.call_args[0][0]
        assert args.type == "mention"


@pytest.mark.asyncio
async def test_notify_system_respects_system_pref(trigger_service, mock_db_session, users):
    user, _ = users

    with patch.object(
        trigger_service,
        "_get_user_preferences",
        return_value={"inApp": {"system": False}},
    ):
        await trigger_service.notify_system(user=user, title="Maintenance", message="Soon")

        mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_grouping_existing_notification(trigger_service, mock_db_session, users):
    assigner, assignee = users

    # Mock finding existing notification
    existing_notif = Notification(
        id=uuid.uuid4(), type="task_updated", data={"count": 1, "items": []}
    )

    with (
        patch.object(
            trigger_service, "_get_user_preferences", return_value={"inApp": {"tasks": True}}
        ),
        patch.object(
            trigger_service, "_find_existing_group_notification", return_value=existing_notif
        ),
    ):
        await trigger_service.notify_task_status_changed(
            task_id=uuid.uuid4(),
            task_title="Test Task",
            project_id=uuid.uuid4(),
            old_status="todo",
            new_status="in_progress",
            changer=assigner,
            assignee=assignee,
        )

        # Should update existing, not create new
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_called_once()
        assert existing_notif.data["count"] == 2
