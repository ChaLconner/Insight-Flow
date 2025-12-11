from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.user import User
from models.project import Project, ProjectMember, MemberRole
from models.task import Task, TaskStatus
import uuid
from datetime import datetime

def test_create_task_authorized(client: TestClient, db_session: Session, test_user: User, test_user_token: str):
    # 1. Create a project owner by test_user
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

    # 2. Create task
    response = client.post(
        "/tasks/",
        headers={"Authorization": f"Bearer {test_user_token}"},
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

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Task"
    assert data["createdBy"] == str(test_user.id)

def test_create_task_via_project_endpoint(client: TestClient, db_session: Session, test_user: User, test_user_token: str):
    # 1. Create project
    project = Project(name="Project Endpoint Test", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    
    member = ProjectMember(project_id=project.id, user_id=test_user.id, role=MemberRole.OWNER.value)
    db_session.add(member)
    db_session.commit()
    
    # 2. Create task via project endpoint
    response = client.post(
        f"/projects/{project.id}/tasks",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "Project Scoped Task",
            "description": "Created via /projects/{id}/tasks",
            "status": "todo",
            "priority": "high",
            "type": "bug",
            "project_id": str(project.id) # Redundant but potentially required by schema?
            # actually schema TaskCreate requires project_id but the endpoint might inject it?
            # Let's check router.
        }
    )
    
    # Check router signature: router.post("/projects/{project_id}/tasks") -> create_task_for_project
    # task_data: TaskCreate. TaskCreate requires project_id.
    # Usually the endpoint overrides it with path param.
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Project Scoped Task"
    assert data["projectId"] == str(project.id)
    assert data["priority"] == "high"

def test_update_task_authorized(client: TestClient, db_session: Session, test_user: User, test_user_token: str):
    # Create project and task
    project = Project(name="Update Proj", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    
    # Add user as member/owner explicitly
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
        f"/tasks/{task.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"title": "Updated Title"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"

def test_delete_task_authorized(client: TestClient, db_session: Session, test_user: User, test_user_token: str):
    project = Project(name="Del Proj", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()

    # Add user as member/owner explicitly
    member = ProjectMember(project_id=project.id, user_id=test_user.id, role=MemberRole.OWNER.value)
    db_session.add(member)
    db_session.commit()
    
    task = Task(title="To Delete", project_id=project.id, created_by=test_user.id)
    db_session.add(task)
    db_session.commit()

    response = client.delete(
        f"/tasks/{task.id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    assert db_session.query(Task).filter_by(id=task.id).first() is None

def test_unauthorized_access_to_others_task(client: TestClient, db_session: Session, test_user: User, test_user_token: str):
    # Create another user and their project/task
    other_user = User(
        email="other@example.com", 
        hashed_password="hash", 
        name="Other",
        is_active=True # Ensure active
    )
    db_session.add(other_user)
    db_session.commit()
    
    other_project = Project(name="Other Proj", owner_id=other_user.id)
    db_session.add(other_project)
    db_session.commit()
    
    other_task = Task(title="Secret Task", project_id=other_project.id, created_by=other_user.id)
    db_session.add(other_task)
    db_session.commit()

    # Try to read task
    response = client.get(
        f"/tasks/{other_task.id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    # Should be 403 Forbidden (Not a member)
    assert response.status_code == 403

    # Try to update task
    response = client.put(
        f"/tasks/{other_task.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"title": "Hacked"}
    )
    assert response.status_code == 403

    # Try to delete task
    response = client.delete(
        f"/tasks/{other_task.id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 403

def test_get_tasks_pagination(client: TestClient, db_session: Session, test_user: User, test_user_token: str):
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
    response = client.get(
        f"/tasks/?limit=2",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "hasMore" in data # camelCase
    
    # Verify values
    assert len(data["items"]) == 2
    assert data["total"] >= 5
    assert data["size"] == 2
    assert data["hasMore"] is True
    
    # 3. Get next page
    response = client.get(
        f"/tasks/?limit=2&skip=2",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["page"] == 2
