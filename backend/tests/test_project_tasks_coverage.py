from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from async_dependencies import require_project_member
from database import get_async_db
from dependencies.services import get_notification_service, get_project_service, get_task_service
from main import app
from models.project import Project
from models.task import Task
from models.user import User
from routers.auth import get_current_active_user

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_task_service():
    service = MagicMock()
    service.get_project_tasks = AsyncMock()
    service.create_task = AsyncMock()
    service.get_task_by_id = AsyncMock()
    service.update_task = AsyncMock()
    service.delete_task = AsyncMock()
    service.update_task_status = AsyncMock()
    service.assign_task = AsyncMock()
    return service


@pytest.fixture
def mock_project_service():
    service = MagicMock()
    service.is_project_member = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_notification_service():
    service = MagicMock()
    service.notify_task_assigned = AsyncMock()
    service.notify_task_status_changed = AsyncMock()
    service.notify_task_completed = AsyncMock()
    return service


@pytest.fixture
def mock_current_user():
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    user.role = "user"
    user.is_active = True
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    # Set optional fields to None to avoid MagicMock returning mocks
    user.first_name = None
    user.last_name = None
    user.username = None
    user.avatar_url = None
    user.phone = None
    user.bio = None
    user.location = None
    user.website = None
    user.last_login_at = None
    user.google_id = None
    user.github_id = None
    user.plan = None
    return user


@pytest.fixture
def mock_project(mock_current_user):
    project = MagicMock(spec=Project)
    project.id = uuid4()
    project.name = "Test Project"
    project.description = "Test Description"
    project.owner_id = mock_current_user.id
    project.is_active = True
    project.created_at = datetime.now(UTC)
    project.updated_at = datetime.now(UTC)
    project.member_ids = [mock_current_user.id]
    return project


@pytest.fixture
def mock_task_factory(mock_project, mock_current_user):
    def create_mock_task():
        task = MagicMock(spec=Task)
        task.id = uuid4()
        task.title = "Test Task"
        task.description = "Test Description"
        # Use strings to avoid Pydantic validation issues with MagicMock + Enum + from_attributes
        task.status = "todo"
        task.priority = "medium"
        task.type = "feature"
        task.project_id = mock_project.id
        task.created_by = mock_current_user.id
        task.assignee_id = None
        task.due_date = None
        task.created_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        # For details response
        task.assignee = None
        task.creator = mock_current_user
        task.project = mock_project
        return task

    return create_mock_task


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.first.return_value = None
    session.execute = AsyncMock(return_value=execute_result)
    return session


@pytest.fixture
def client(
    mock_task_service,
    mock_project_service,
    mock_notification_service,
    mock_db_session,
    mock_current_user,
    mock_project,
):
    # Override dependencies
    app.dependency_overrides[get_task_service] = lambda: mock_task_service
    app.dependency_overrides[get_project_service] = lambda: mock_project_service
    app.dependency_overrides[get_notification_service] = lambda: mock_notification_service
    app.dependency_overrides[get_async_db] = lambda: mock_db_session
    app.dependency_overrides[get_current_active_user] = lambda: mock_current_user
    app.dependency_overrides[require_project_member] = lambda: mock_project

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


# ============================================================================
# Tests
# ============================================================================


def test_get_project_tasks_success(client, mock_project, mock_task_service, mock_task_factory):
    task = mock_task_factory()
    mock_task_service.get_project_tasks.return_value = ([task], 1)

    response = client.get(f"/api/v1/projects/{mock_project.id}/tasks")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Test Task"


def test_get_project_tasks_exception(client, mock_project, mock_task_service):
    mock_task_service.get_project_tasks.side_effect = Exception("DB Error")

    response = client.get(f"/api/v1/projects/{mock_project.id}/tasks")

    assert response.status_code == 500
    assert "Failed to fetch project tasks" in response.json()["message"]
    assert "DB Error" not in response.text


def test_create_task_success(client, mock_project, mock_task_service, mock_task_factory):
    task = mock_task_factory()
    task.title = "New Task"
    mock_task_service.create_task.return_value = task

    payload = {
        "title": "New Task",
        "description": "Desc",
        "status": "todo",
        "priority": "medium",
        "type": "feature",
        "project_id": str(mock_project.id),
    }

    response = client.post(f"/api/v1/projects/{mock_project.id}/tasks", json=payload)

    assert response.status_code == 200
    assert response.json()["title"] == "New Task"


def test_create_task_with_assignee_sends_notification(
    client, mock_project, mock_task_service, mock_task_factory
):
    task = mock_task_factory()
    assignee = User(id=uuid4(), email="assignee@example.com", name="Assignee")
    task.assignee_id = assignee.id
    task.assignee = assignee
    mock_task_service.create_task.return_value = task

    payload = {
        "title": "Assigned Task",
        "description": "Desc",
        "status": "todo",
        "priority": "medium",
        "type": "feature",
        "project_id": str(mock_project.id),
        "assignee_id": str(assignee.id),
    }

    with patch("routers.project_tasks.enqueue_job", new_callable=AsyncMock) as mock_enqueue:
        response = client.post(f"/api/v1/projects/{mock_project.id}/tasks", json=payload)

        assert response.status_code == 200
        mock_enqueue.assert_awaited_once()


def test_create_task_value_error(client, mock_project, mock_task_service):
    mock_task_service.create_task.side_effect = ValueError("Invalid Input")

    payload = {"title": "New Task", "project_id": str(mock_project.id)}

    response = client.post(f"/api/v1/projects/{mock_project.id}/tasks", json=payload)

    assert response.status_code == 400
    # ValueError handler returns message. It is either sanitised or not.
    # Exception handler logic: "Invalid request" if not in safe list.
    # "Invalid Input" is NOT in safe list -> returns "Invalid request".
    # BUT, wait. Last run said: assert 'Invalid Input' == 'Invalid...'.
    # This means Actual was 'Invalid Input'.
    # Why? Maybe I mocked it differently?
    # Router: except ValueError as e: raise HTTPException(..., detail=str(e))
    # Exception Handler: HTTPException -> message=str(exc.detail).
    # YES. It goes to http_exception_handler, NOT value_error_handler!
    # Because router CATCHES ValueError and RAISES HTTPException.
    # So it just passes the string through.
    assert response.json()["message"] == "Invalid Input"


def test_read_project_task_success(client, mock_project, mock_task_service, mock_task_factory):
    task = mock_task_factory()
    mock_task_service.get_task_by_id.return_value = task

    response = client.get(f"/api/v1/projects/{mock_project.id}/tasks/{task.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(task.id)


def test_read_project_task_not_found_in_project(
    client, mock_project, mock_task_service, mock_task_factory
):
    task = mock_task_factory()
    task.project_id = uuid4()  # Different project
    mock_task_service.get_task_by_id.return_value = task

    response = client.get(f"/api/v1/projects/{mock_project.id}/tasks/{task.id}")

    assert response.status_code == 404
    assert response.json()["message"] == "Task not found in this project"


def test_read_project_task_not_found(client, mock_project, mock_task_service):
    mock_task_service.get_task_by_id.return_value = None

    response = client.get(f"/api/v1/projects/{mock_project.id}/tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["message"] == "Task not found"


def test_update_project_task_success(client, mock_project, mock_task_service, mock_task_factory):
    task = mock_task_factory()
    mock_task_service.get_task_by_id.return_value = task
    mock_task_service.update_task.return_value = task

    payload = {"title": "Updated"}
    response = client.put(f"/api/v1/projects/{mock_project.id}/tasks/{task.id}", json=payload)

    assert response.status_code == 200


def test_delete_project_task_success(client, mock_project, mock_task_service, mock_task_factory):
    task = mock_task_factory()
    mock_task_service.get_task_by_id.return_value = task

    response = client.delete(f"/api/v1/projects/{mock_project.id}/tasks/{task.id}")

    assert response.status_code == 200
    assert response.json()["message"] == "Task deleted successfully"


def test_update_status_success(client, mock_project, mock_task_service, mock_task_factory):
    task = mock_task_factory()
    task.status = "done"

    mock_task_service.get_task_by_id.return_value = task
    mock_task_service.update_task_status.return_value = task

    response = client.put(
        f"/api/v1/projects/{mock_project.id}/tasks/{task.id}/status", json={"status": "done"}
    )

    assert response.status_code == 200


def test_update_status_sends_notifications(
    client, mock_project, mock_task_service, mock_task_factory
):
    task = mock_task_factory()
    assignee = User(id=uuid4(), email="assignee@example.com", name="Assignee")
    creator = User(id=uuid4(), email="creator@example.com", name="Creator")
    task.status = "todo"
    task.assignee = assignee
    task.creator = creator
    task.assignee_id = assignee.id
    task.created_by = creator.id

    updated_task = mock_task_factory()
    updated_task.id = task.id
    updated_task.title = task.title
    updated_task.project_id = task.project_id
    updated_task.project = task.project
    updated_task.status = "done"
    updated_task.assignee = assignee
    updated_task.creator = creator

    mock_task_service.get_task_by_id.return_value = task
    mock_task_service.update_task_status.return_value = updated_task

    with patch("routers.project_tasks.enqueue_job", new_callable=AsyncMock) as mock_enqueue:
        response = client.put(
            f"/api/v1/projects/{mock_project.id}/tasks/{task.id}/status", json={"status": "done"}
        )

        assert response.status_code == 200
        mock_enqueue.assert_awaited_once()


def test_update_status_missing_field(client, mock_project):
    response = client.put(f"/api/v1/projects/{mock_project.id}/tasks/{uuid4()}/status", json={})
    assert response.status_code == 400
    assert response.json()["message"] == "Status is required"


def test_assign_task_success(client, mock_project, mock_task_service, mock_task_factory):
    task = mock_task_factory()
    mock_task_service.get_task_by_id.return_value = task
    mock_task_service.assign_task.return_value = task

    response = client.put(
        f"/api/v1/projects/{mock_project.id}/tasks/{task.id}/assign",
        json={"assignee_id": str(uuid4())},
    )

    assert response.status_code == 200


def test_assign_task_sends_notification(
    client,
    mock_project,
    mock_task_service,
    mock_db_session,
    mock_task_factory,
):
    task = mock_task_factory()
    assignee = User(id=uuid4(), email="assigned@example.com", name="Assigned User")
    task.project = mock_project
    updated_task = mock_task_factory()
    updated_task.id = task.id
    updated_task.project = mock_project
    updated_task.project_id = mock_project.id
    updated_task.title = task.title

    mock_task_service.get_task_by_id.return_value = task
    mock_task_service.assign_task.return_value = updated_task

    execute_result = MagicMock()
    execute_result.scalars.return_value.first.return_value = assignee
    mock_db_session.execute.return_value = execute_result

    with patch("routers.project_tasks.enqueue_job", new_callable=AsyncMock) as mock_enqueue:
        response = client.put(
            f"/api/v1/projects/{mock_project.id}/tasks/{task.id}/assign",
            json={"assignee_id": str(assignee.id)},
        )

        assert response.status_code == 200
        mock_enqueue.assert_awaited_once()


def test_assign_task_not_member(client, mock_project, mock_project_service):
    # Override is_project_member to return False
    mock_project_service.is_project_member.return_value = False

    response = client.put(
        f"/api/v1/projects/{mock_project.id}/tasks/{uuid4()}/assign",
        json={"assignee_id": str(uuid4())},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Not a member of this project"


def test_read_task_not_member(client, mock_project, mock_project_service):
    mock_project_service.is_project_member.return_value = False

    response = client.get(f"/api/v1/projects/{mock_project.id}/tasks/{uuid4()}")

    assert response.status_code == 403
