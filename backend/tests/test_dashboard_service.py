"""
Unit tests for DashboardService.
"""
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from models.project import Project, ProjectMember, MemberRole
from models.task import Task, TaskStatus, TaskPriority, TaskType
from models.task_history import TaskHistory, ActivityType
from services.dashboard_service import DashboardService


class TestDashboardService:
    """Test cases for DashboardService."""

    @pytest.fixture
    def dashboard_service(self, db_session):
        """Create DashboardService instance."""
        return DashboardService(db_session)

    @pytest.fixture
    def setup_dashboard_data(self, db_session, test_user):
        """Set up test data for dashboard tests."""
        # Create projects
        projects = []
        for i in range(3):
            project = Project(
                name=f"Project {i}",
                description=f"Description {i}",
                owner_id=test_user.id,
                is_active=True
            )
            db_session.add(project)
            projects.append(project)
        
        db_session.commit()
        
        # Create tasks for each project
        tasks = []
        statuses = [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE]
        for project in projects:
            for j, status in enumerate(statuses):
                task = Task(
                    title=f"Task {j} for {project.name}",
                    project_id=project.id,
                    created_by=test_user.id,
                    status=status,
                    priority=TaskPriority.MEDIUM,
                    type=TaskType.FEATURE
                )
                db_session.add(task)
                tasks.append(task)
        
        db_session.commit()
        
        return {
            "user": test_user,
            "projects": projects,
            "tasks": tasks,
            "service": DashboardService(db_session)
        }

    def test_get_overview_stats(self, db_session, setup_dashboard_data):
        """Test getting dashboard overview statistics."""
        service = setup_dashboard_data["service"]
        user = setup_dashboard_data["user"]
        
        stats = service.get_overview_stats(user.id)
        
        assert stats is not None
        assert "totalProjects" in stats
        assert "totalTasks" in stats
        assert "completedTasks" in stats
        assert "inProgressTasks" in stats
        
        # We created 3 projects
        assert stats["totalProjects"] == 3
        
        # We created 9 tasks (3 per project)
        assert stats["totalTasks"] == 9
        
        # 3 tasks are DONE (1 per project)
        assert stats["completedTasks"] == 3

    def test_get_overview_stats_empty(self, db_session, test_user, dashboard_service):
        """Test overview stats with no data."""
        stats = dashboard_service.get_overview_stats(test_user.id)
        
        assert stats is not None
        assert stats["totalProjects"] == 0
        assert stats["totalTasks"] == 0

    def test_get_recent_projects(self, db_session, setup_dashboard_data):
        """Test getting recent projects."""
        service = setup_dashboard_data["service"]
        user = setup_dashboard_data["user"]
        
        projects = service.get_recent_projects(user.id, limit=5)
        
        assert len(projects) == 3
        
        for project in projects:
            assert "id" in project
            assert "name" in project
            assert "progress" in project  # DashboardService returns 'progress' not 'task_count'

    def test_get_recent_projects_limit(self, db_session, setup_dashboard_data):
        """Test recent projects with limit."""
        service = setup_dashboard_data["service"]
        user = setup_dashboard_data["user"]
        
        projects = service.get_recent_projects(user.id, limit=2)
        
        assert len(projects) == 2

    def test_get_recent_activities(self, db_session, setup_dashboard_data):
        """Test getting recent activities."""
        service = setup_dashboard_data["service"]
        user = setup_dashboard_data["user"]
        tasks = setup_dashboard_data["tasks"]
        
        # Create some task history entries
        for task in tasks[:3]:
            history = TaskHistory(
                task_id=task.id,
                project_id=task.project_id,
                user_id=user.id,
                activity_type=ActivityType.TASK_CREATED,
                description=f"Created task: {task.title}"
            )
            db_session.add(history)
        
        db_session.commit()
        
        activities = service.get_recent_activities(user.id, limit=10)
        
        assert len(activities) >= 3

    def test_get_recent_activities_empty(self, db_session, test_user, dashboard_service):
        """Test recent activities with no data."""
        activities = dashboard_service.get_recent_activities(test_user.id)
        
        assert activities == [] or len(activities) == 0

    def test_calculate_percentage_change(self, db_session, dashboard_service):
        """Test percentage change calculation."""
        # Positive change
        result = dashboard_service._calculate_percentage_change(10, 5)
        assert result == 100.0  # 100% increase
        
        # Negative change
        result = dashboard_service._calculate_percentage_change(5, 10)
        assert result == -50.0  # 50% decrease
        
        # No previous value
        result = dashboard_service._calculate_percentage_change(10, 0)
        assert result == 100.0  # Default to 100% if no previous

    def test_format_change(self, db_session, dashboard_service):
        """Test change formatting."""
        # Positive
        result = dashboard_service._format_change(25.5)
        assert "+" in result or "25" in result
        
        # Negative
        result = dashboard_service._format_change(-15.3)
        assert "-" in result or "15" in result

    def test_projects_accessible_to_member(self, db_session, test_user, dashboard_service):
        """Test that members can see projects they're part of."""
        from models.user import User
        from utils.auth import get_password_hash
        
        # Create another user as project owner
        owner = User(
            email="owner@example.com",
            hashed_password=get_password_hash("password123"),
            name="Project Owner",
            is_active=True
        )
        db_session.add(owner)
        db_session.commit()
        
        # Create a project owned by owner
        project = Project(
            name="Owner's Project",
            description="A project owned by owner",
            owner_id=owner.id,
            is_active=True
        )
        db_session.add(project)
        db_session.commit()
        
        # Add test_user as member
        member = ProjectMember(
            project_id=project.id,
            user_id=test_user.id,
            role=MemberRole.MEMBER.value
        )
        db_session.add(member)
        db_session.commit()
        
        # test_user should see this project
        stats = dashboard_service.get_overview_stats(test_user.id)
        assert stats["totalProjects"] >= 1
        
        # owner should also see it
        owner_stats = dashboard_service.get_overview_stats(owner.id)
        assert owner_stats["totalProjects"] >= 1

    def test_stats_include_assigned_tasks(self, db_session, test_user, dashboard_service):
        """Test that stats include tasks assigned to user."""
        from models.user import User
        from utils.auth import get_password_hash
        
        # Create another user
        other_user = User(
            email="taskowner@example.com",
            hashed_password=get_password_hash("password123"),
            name="Task Owner",
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Create project owned by other_user
        project = Project(
            name="Other User Project",
            description="Project by other user",
            owner_id=other_user.id,
            is_active=True
        )
        db_session.add(project)
        db_session.commit()
        
        # Add test_user as member
        member = ProjectMember(
            project_id=project.id,
            user_id=test_user.id,
            role=MemberRole.MEMBER.value
        )
        db_session.add(member)
        db_session.commit()
        
        # Create task assigned to test_user
        task = Task(
            title="Assigned to Test User",
            project_id=project.id,
            created_by=other_user.id,
            assignee_id=test_user.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            type=TaskType.BUG
        )
        db_session.add(task)
        db_session.commit()
        
        # test_user should see this in their stats
        stats = dashboard_service.get_overview_stats(test_user.id)
        assert stats["totalTasks"] >= 1
