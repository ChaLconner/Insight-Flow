import pytest
from services.project_service import ProjectService
from models.user import User
from models.project import Project, ProjectMember, MemberRole
from models.task import Task
from datetime import datetime

@pytest.fixture
def sample_user(db_session):
    user = User(
        email="test@example.com",
        name="Test User",
        google_id="123456",
        avatar_url="http://example.com/avatar.jpg"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def second_user(db_session):
    user = User(
        email="other@example.com",
        name="Other User",
        google_id="789012"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_get_projects_with_stats_batching(db_session, sample_user, second_user):
    """
    Test that get_projects_with_stats correctly aggregates members and stats,
    verifying the manual batching logic in the service.
    """
    # 1. Create Projects
    project1 = Project(
        name="Project 1",
        description="Test Project 1",
        owner_id=sample_user.id
    )
    db_session.add(project1)
    
    project2 = Project(
        name="Project 2",
        description="Test Project 2",
        owner_id=sample_user.id
    )
    db_session.add(project2)
    db_session.commit()
    
    # 2. Add Members
    # Project 1 has 2 members (Owner + Second)
    # Note: Model stores role as String, using .value
    pm1 = ProjectMember(project_id=project1.id, user_id=sample_user.id, role=MemberRole.OWNER.value)
    pm2 = ProjectMember(project_id=project1.id, user_id=second_user.id, role=MemberRole.MEMBER.value)
    
    # Project 2 only has Owner
    pm3 = ProjectMember(project_id=project2.id, user_id=sample_user.id, role=MemberRole.OWNER.value)
    
    db_session.add_all([pm1, pm2, pm3])
    db_session.commit()
    
    # 3. Add Tasks to verify basic stats
    task = Task(
        title="Task 1",
        project_id=project1.id,
        created_by=sample_user.id,
        status="todo",
        priority="high",
        type="task"
    )
    db_session.add(task)
    db_session.commit()
    
    # 4. Call Service
    service = ProjectService(db_session)
    results = service.get_projects_with_stats(
        user_id=sample_user.id,
        skip=0,
        limit=10
    )
    
    # 5. Verify Results
    assert len(results) == 2
    
    # Sort results by ID to ensure deterministic checks
    results.sort(key=lambda x: x["project"].id)
    p1_result = results[0] if results[0]["project"].id == project1.id else results[1]
    p2_result = results[1] if results[1]["project"].id == project2.id else results[0]
    
    # Check Project 1 Stats
    assert p1_result["project"].name == "Project 1"
    assert p1_result["task_count"] == 1
    assert p1_result["member_count"] == 2
    assert len(p1_result["members"]) == 2
    
    # Verify members content (members are ProjectMember objects, joined with user)
    # The member object has a .user relationship loaded
    member_names = [m.user.name for m in p1_result["members"]]
    assert "Test User" in member_names
    assert "Other User" in member_names

    # Check Project 2 Stats
    assert p2_result["project"].name == "Project 2"
    assert p2_result["task_count"] == 0
    assert p2_result["member_count"] == 1
    assert len(p2_result["members"]) == 1
    assert p2_result["members"][0].user.name == "Test User"
