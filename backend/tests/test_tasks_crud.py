"""
Task CRUD tests.
Uses client fixture which already overrides authentication.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

# Import directly from async_dependencies to match routers
from async_dependencies import get_async_authorized_task, require_project_member
from dependencies import get_project_service, get_task_service
from main import app
from models.project import Project
from models.task import Task, TaskStatus
from models.user import User

# Note: Routers use get_async_authorized_task, so distinct from get_authorized_task in name,
# even if logic is same object. We must override key used in router.


def test_create_task_authorized(client: TestClient, db_session: Session, test_user: User):
    """Test creating a task as project owner."""

    mock_project_service = MagicMock()
    mock_project_service.get_project_with_member_check = AsyncMock(
        return_value=MagicMock(id=uuid.uuid4())
    )

    mock_task_service = MagicMock()
    task_id = uuid.uuid4()

    mock_task_service.create_task = AsyncMock(
        return_value=Task(
            id=task_id,
            title="New Task",
            description="Task Description",
            status=TaskStatus.TODO,
            priority="medium",
            type="feature",
            project_id=uuid.uuid4(),
            created_by=test_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )

    app.dependency_overrides[get_project_service] = lambda: mock_project_service
    app.dependency_overrides[get_task_service] = lambda: mock_task_service

    response = client.post(
        "/api/v1/tasks/",
        json={
            "title": "New Task",
            "description": "Task Description",
            "project_id": str(uuid.uuid4()),
            "status": "todo",
            "priority": "medium",
            "type": "feature",
            "due_date": datetime.now().isoformat(),
        },
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.json()}"
    )
    data = response.json()
    assert data["title"] == "New Task"

    del app.dependency_overrides[get_project_service]
    del app.dependency_overrides[get_task_service]


def test_create_task_via_project_endpoint(client: TestClient, db_session: Session, test_user: User):
    """Test creating a task via project endpoint."""
    mock_project_service = MagicMock()

    mock_task_service = MagicMock()
    mock_task_service.create_task = AsyncMock(
        return_value=Task(
            id=uuid.uuid4(),
            title="Project Scoped Task",
            description="Created via /projects/{id}/tasks",
            status=TaskStatus.TODO,
            priority="high",
            type="bug",
            project_id=uuid.uuid4(),
            created_by=test_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )

    # Use require_project_member from async_dependencies
    app.dependency_overrides[get_project_service] = lambda: mock_project_service
    app.dependency_overrides[get_task_service] = lambda: mock_task_service
    app.dependency_overrides[require_project_member] = lambda: MagicMock(id=uuid.uuid4())

    response = client.post(
        f"/api/v1/projects/{uuid.uuid4()}/tasks",
        json={
            "title": "Project Scoped Task",
            "description": "Created via /projects/{id}/tasks",
            "status": "todo",
            "priority": "high",
            "type": "bug",
            "project_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.json()}"
    )
    data = response.json()
    assert data["title"] == "Project Scoped Task"

    del app.dependency_overrides[get_project_service]
    del app.dependency_overrides[get_task_service]
    del app.dependency_overrides[require_project_member]


def test_update_task_authorized(client: TestClient, db_session: Session, test_user: User):
    """Test updating a task as project owner."""
    mock_task_service = MagicMock()
    mock_task_service.update_task = AsyncMock(
        return_value=Task(
            id=uuid.uuid4(),
            title="Updated Title",
            description="Task Description",
            status=TaskStatus.TODO,
            priority="medium",
            type="feature",
            project_id=uuid.uuid4(),
            created_by=test_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )

    app.dependency_overrides[get_task_service] = lambda: mock_task_service
    # Use get_async_authorized_task from async_dependencies
    app.dependency_overrides[get_async_authorized_task] = lambda: MagicMock(id=uuid.uuid4())

    response = client.put(f"/api/v1/tasks/{uuid.uuid4()}", json={"title": "Updated Title"})
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.json()}"
    )
    assert response.json()["title"] == "Updated Title"

    del app.dependency_overrides[get_task_service]
    del app.dependency_overrides[get_async_authorized_task]


def test_delete_task_authorized(client: TestClient, db_session: Session, test_user: User):
    """Test deleting a task."""
    mock_task_service = MagicMock()
    mock_task_service.delete_task = AsyncMock(return_value=True)

    app.dependency_overrides[get_task_service] = lambda: mock_task_service
    app.dependency_overrides[get_async_authorized_task] = lambda: MagicMock(id=uuid.uuid4())

    response = client.delete(f"/api/v1/tasks/{uuid.uuid4()}")
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.json()}"
    )

    del app.dependency_overrides[get_task_service]
    del app.dependency_overrides[get_async_authorized_task]


def test_unauthorized_access_to_others_task(
    client: TestClient, db_session: Session, test_user: User
):
    """Test that users cannot access tasks from projects they're not a member of."""

    def mock_get_authorized_task_forbidden():
        raise HTTPException(status_code=403, detail="Not authorized")

    app.dependency_overrides[get_async_authorized_task] = mock_get_authorized_task_forbidden

    response = client.get(f"/api/v1/tasks/{uuid.uuid4()}")

    assert response.status_code == 403, (
        f"Expected 403, got {response.status_code}: {response.json()}"
    )

    del app.dependency_overrides[get_async_authorized_task]


def test_get_tasks_pagination(client: TestClient, db_session: Session, test_user: User):
    """Test task pagination."""
    mock_task_service = MagicMock()
    tasks = [
        Task(
            id=uuid.uuid4(),
            title=f"Task {i}",
            description="Desc",
            status=TaskStatus.TODO,
            priority="medium",
            type="feature",
            project_id=uuid.uuid4(),
            created_by=test_user.id,
            creator=test_user,
            project=Project(
                id=uuid.uuid4(),
                name="Test Project",
                owner_id=test_user.id,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            assignee=test_user,  # Optional but good
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        for i in range(2)
    ]

    # Correct method calls - get_user_tasks for global list
    mock_task_service.get_user_tasks = AsyncMock(return_value=(tasks, 5))

    app.dependency_overrides[get_task_service] = lambda: mock_task_service

    # 2. Get tasks with limit 2
    response = client.get("/api/v1/tasks/?limit=2")
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.json()}"
    )
    data = response.json()

    # Verify structure
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data

    # Verify values
    assert len(data["items"]) == 2
    assert data["total"] >= 5

    del app.dependency_overrides[get_task_service]
