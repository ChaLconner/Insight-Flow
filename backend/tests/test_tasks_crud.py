"""
Task CRUD tests.
Uses client fixture which already overrides authentication.
"""
from starlette.testclient import TestClient
from sqlalchemy.orm import Session
from models.user import User
from models.project import Project, ProjectMember, MemberRole
from models.task import Task, TaskStatus
import uuid
from datetime import datetime


def test_create_task_authorized(client: TestClient, db_session: Session, test_user: User):
    """Test creating a task as project owner."""
    # 1. Create a project owned by test_user
    project = Project(
        name="Test Project Task",
        description="Desc",
        owner_id=test_user.id
    )
    db_session.add(project)
    db_session.commit()
    
    # Add user as member/owner explicitly
    member = ProjectMember(project_id=project.id, user_id=test_user.id, role=MemberRole.OWNER.value)
    db_session.add(member)
    db_session.commit()

    # 2. Create task - client fixture already has auth override
    response = client.post(
        "/api/v1/tasks/",
        json={
            "title": "New Task",
            "description": "Task Description",
            "project_id": str(project.id),
            "status": "todo",
            "priority": "medium",
            "type": "feature",
            "due_date": datetime.now().isoformat()
        }
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["title"] == "New Task"


def test_create_task_via_project_endpoint(client: TestClient, db_session: Session, test_user: User):
    """Test creating a task via project endpoint."""
    # 1. Create project
    project = Project(name="Project Endpoint Test", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    
    member = ProjectMember(project_id=project.id, user_id=test_user.id, role=MemberRole.OWNER.value)
    db_session.add(member)
    db_session.commit()
    
    # 2. Create task via project endpoint - no auth header needed
    response = client.post(
        f"/api/v1/projects/{project.id}/tasks",
        json={
            "title": "Project Scoped Task",
            "description": "Created via /projects/{id}/tasks",
            "status": "todo",
            "priority": "high",
            "type": "bug",
            "project_id": str(project.id)
        }
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["title"] == "Project Scoped Task"


def test_update_task_authorized(client: TestClient, db_session: Session, test_user: User):
    """Test updating a task as project owner."""
    # Create project and task
    project = Project(name="Update Proj", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    
    member = ProjectMember(project_id=project.id, user_id=test_user.id, role=MemberRole.OWNER.value)
    db_session.add(member)
    db_session.commit()
    
    task = Task(
        title="Original Title",
        project_id=project.id,
        created_by=test_user.id,
        status=TaskStatus.TODO
    )
    db_session.add(task)
    db_session.commit()

    response = client.put(
        f"/api/v1/tasks/{task.id}",
        json={"title": "Updated Title"}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    assert response.json()["title"] == "Updated Title"


def test_delete_task_authorized(client: TestClient, db_session: Session, test_user: User):
    """Test deleting a task as project owner."""
    project = Project(name="Del Proj", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()

    member = ProjectMember(project_id=project.id, user_id=test_user.id, role=MemberRole.OWNER.value)
    db_session.add(member)
    db_session.commit()
    
    task = Task(title="To Delete", project_id=project.id, created_by=test_user.id)
    db_session.add(task)
    db_session.commit()

    response = client.delete(f"/api/v1/tasks/{task.id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    assert db_session.query(Task).filter_by(id=task.id).first() is None


def test_unauthorized_access_to_others_task(client: TestClient, db_session: Session, test_user: User, unauthenticated_client: TestClient):
    """Test that users cannot access tasks from projects they're not a member of."""
    # Create another user and their project/task
    from utils.auth import get_password_hash
    
    other_user = User(
        email="other@example.com", 
        hashed_password=get_password_hash("password"),
        name="Other",
        is_active=True
    )
    db_session.add(other_user)
    db_session.commit()
    
    other_project = Project(name="Other Proj", owner_id=other_user.id)
    db_session.add(other_project)
    db_session.commit()
    
    other_task = Task(title="Secret Task", project_id=other_project.id, created_by=other_user.id)
    db_session.add(other_task)
    db_session.commit()

    # Try to read task with authenticated client (test_user)
    # test_user is NOT a member of other_project
    response = client.get(f"/api/v1/tasks/{other_task.id}")
    
    # Should be 403 Forbidden (Not a member)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.json()}"


def test_get_tasks_pagination(client: TestClient, db_session: Session, test_user: User):
    """Test task pagination."""
    # 1. Create a project and some tasks
    project = Project(name="Page Proj", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    
    # Add user as member
    member = ProjectMember(project_id=project.id, user_id=test_user.id, role=MemberRole.OWNER.value)
    db_session.add(member)
    db_session.commit()
    
    # Create 5 tasks
    for i in range(5):
        task = Task(title=f"Task {i}", project_id=project.id, created_by=test_user.id)
        db_session.add(task)
    db_session.commit()
    
    # 2. Get tasks with limit 2
    response = client.get("/api/v1/tasks/?limit=2")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    
    # Verify structure
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "hasMore" in data
    
    # Verify values
    assert len(data["items"]) == 2
    assert data["total"] >= 5
    assert data["size"] == 2
    assert data["hasMore"] is True
    
    # 3. Get next page
    response = client.get("/api/v1/tasks/?limit=2&skip=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["page"] == 2
