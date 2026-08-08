from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from async_dependencies import get_async_authorized_task
from database import get_async_db
from dependencies.services import get_notification_service
from main import app
from models.analytics import TaskComment
from models.project import Project
from models.task import Task
from models.user import User
from routers.auth import get_current_active_user


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    async def refresh_side_effect(instance):
        if getattr(instance, "id", None) is None:
            instance.id = uuid4()
        now = datetime.now(UTC)
        if getattr(instance, "created_at", None) is None:
            instance.created_at = now
        if getattr(instance, "updated_at", None) is None:
            instance.updated_at = now

    session.refresh = AsyncMock(side_effect=refresh_side_effect)
    return session


@pytest.fixture
def mock_notification_service():
    service = MagicMock()
    service.notify_mention = AsyncMock()
    return service


@pytest.fixture
def current_user():
    return User(
        id=uuid4(),
        email="author@example.com",
        username="author",
        name="Author User",
        role="member",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def authorized_task(current_user):
    project = Project(id=uuid4(), name="Test Project", owner_id=current_user.id)
    task = Task(
        id=uuid4(),
        title="Test Task",
        project_id=project.id,
        created_by=current_user.id,
    )
    task.project = project
    task.creator = current_user
    task.assignee = None
    return task


@pytest.fixture
def client(mock_db_session, mock_notification_service, current_user, authorized_task):
    async def override_db():
        return mock_db_session

    async def override_notification_service():
        return mock_notification_service

    async def override_current_user():
        return current_user

    async def override_authorized_task():
        return authorized_task

    app.dependency_overrides[get_async_db] = override_db
    app.dependency_overrides[get_notification_service] = override_notification_service
    app.dependency_overrides[get_current_active_user] = override_current_user
    app.dependency_overrides[get_async_authorized_task] = override_authorized_task

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_list_task_comments(client, mock_db_session, current_user, authorized_task):
    comment = TaskComment(
        id=uuid4(),
        task_id=authorized_task.id,
        user_id=current_user.id,
        content="hello @teammate",
    )
    comment.user = current_user
    comment.created_at = datetime.now(UTC)
    comment.updated_at = datetime.now(UTC)

    result = MagicMock()
    result.scalars.return_value.all.return_value = [comment]
    mock_db_session.execute.return_value = result

    response = client.get(f"/api/v1/tasks/{authorized_task.id}/comments")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["mentions"] == ["teammate"]


def test_create_task_comment_triggers_mention_notifications(
    client, mock_db_session, current_user, authorized_task
):
    mentioned_user = User(
        id=uuid4(),
        email="teammate@example.com",
        username="teammate",
        name="Team Mate",
        role="member",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = MagicMock()
    result.scalars.return_value.all.return_value = [mentioned_user]
    mock_db_session.execute.return_value = result

    with patch("routers.tasks.enqueue_job", new_callable=AsyncMock) as mock_enqueue:
        response = client.post(
            f"/api/v1/tasks/{authorized_task.id}/comments",
            json={"content": "Please review this, @teammate"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["mentions"] == ["teammate"]
        mock_enqueue.assert_awaited_once()
