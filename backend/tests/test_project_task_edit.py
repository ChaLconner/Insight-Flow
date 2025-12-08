import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from main import app
from database import get_db, Base
from models.user import User
from models.project import Project, ProjectMember, MemberRole as ProjectRole
from models.task import Task, TaskStatus, TaskPriority, TaskType
from services.task_service import TaskService
from schemas.task import TaskUpdate, TaskStatusUpdate
from utils.auth import create_access_token

# Use existing conftest fixtures: client, test_user, test_user_token, db_session

def test_project_task_edit_flow(client: TestClient, db_session: Session, test_user: User, test_user_token: str):
    """
    Test the complete flow of editing a task within a project.
    1. Create a project
    2. Add task to project
    3. Edit task (title, description, etc.)
    4. Verify updates
    5. Verify status update
    """
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # 1. Create a project
    project = Project(
        name="Test Project for Editing",
        description="A project to test task editing",
        owner_id=test_user.id,
        is_active=True
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    
    # Ensure user is a member (Owner is usually implicit but let's be safe for RBAC checks in services)
    # The AuthService or ProjectService usually handles this creation, but here we do it manually or assume owner access.
    # We need to manually add the member since we are bypassing the service
    member = ProjectMember(project_id=project.id, user_id=test_user.id, role=ProjectRole.OWNER.value)
    db_session.add(member)
    db_session.commit()
    
    # 2. Add task to project
    task = Task(
        title="Original Task Title",
        description="Original Description",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        type=TaskType.FEATURE,
        project_id=project.id,
        created_by=test_user.id,
        due_date=datetime.now(timezone.utc) + timedelta(days=5)
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    
    task_id = str(task.id)
    
    # 3. Edit task (General Update: Title, Description, Priority)
    update_payload = {
        "title": "Updated Task Title",
        "description": "Updated Description",
        "priority": "high", # Case insensitive check? Schema usually expects enum value or string
        "type": "bug"
    }
    
    response = client.put(
        f"/tasks/{task_id}",
        json=update_payload,
        headers=headers
    )
    
    assert response.status_code == 200, f"Update failed: {response.text}"
    updated_data = response.json()
    assert updated_data["title"] == "Updated Task Title"
    assert updated_data["description"] == "Updated Description"
    assert updated_data["priority"].lower() == "high"
    assert updated_data["type"].lower() == "bug"
    
    # Verify in DB
    db_session.refresh(task)
    assert task.title == "Updated Task Title"
    assert task.priority == TaskPriority.HIGH
    
    # 4. Edit Task Status (Specific Endpoint or Main Update)
    # Testing specific endpoint first
    status_payload = {"status": "in_progress"}
    response = client.put(
        f"/tasks/{task_id}/status",
        json=status_payload,
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"].lower() == "in_progress"
    
    db_session.refresh(task)
    assert task.status == TaskStatus.IN_PROGRESS

    # 5. Access Control Test: Another user trying to edit
    # Create another user
    other_user = User(
        email="hacker@example.com",
        name="Hacker",
        hashed_password="hashedpassword",
        is_active=True
    )
    db_session.add(other_user)
    db_session.commit()
    
    # Retrieve token for other user (mocking or implementing login helper)
    other_token = create_access_token(data={"sub": str(other_user.id)})
    other_headers = {"Authorization": f"Bearer {other_token}"}
    
    # Attempt update
    response = client.put(
        f"/tasks/{task_id}",
        json={"title": "Hacked Title"},
        headers=other_headers
    )
    
    # Should be 403 Forbidden or 404 Not Found (depending on how get_authorized_task is implemented)
    # get_authorized_task checks if user is member of project. If not, it might return 404 or 403.
    # Looking at dependencies.py (from memory/context): it likely filters by access.
    # If the user can't "see" the task, it's 404. If they can see but not edit, 403.
    # But usually access means "read access". 
    
    assert response.status_code in [403, 404]
    
    # Refresh to ensure no change
    db_session.refresh(task)
    assert task.title == "Updated Task Title"

def test_invalid_task_update(client: TestClient, db_session: Session, test_user: User, test_user_token: str):
    """Test updating with invalid data"""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Create project and task
    project = Project(name="Test P2", owner_id=test_user.id, is_active=True)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    member = ProjectMember(project_id=project.id, user_id=test_user.id, role=ProjectRole.OWNER.value)
    db_session.add(member)
    db_session.commit()
    
    task = Task(title="T1", status=TaskStatus.TODO, project_id=project.id, created_by=test_user.id)
    db_session.add(task)
    db_session.commit()
    
    # Invalid Priority
    response = client.put(
        f"/tasks/{task.id}",
        json={"priority": "INVALID_PRIORITY"},
        headers=headers
    )
    print(f"Invalid priority response code: {response.status_code}")
    print(f"Invalid priority response text: {response.text}")
    assert response.status_code == 422 # Validation error
    
    # Invalid UUID
    response = client.put(
        f"/tasks/invalid-uuid",
        json={"title": "New"},
        headers=headers
    )
    assert response.status_code == 422
