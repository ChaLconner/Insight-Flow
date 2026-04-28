"""
Async Unit tests for AsyncDashboardService.
"""

import pytest

from models.project import Project
from models.task import Task, TaskPriority, TaskStatus, TaskType
from models.task_history import ActivityType, TaskHistory


class TestAsyncDashboardService:
    """Test cases for AsyncDashboardService."""

    @pytest.fixture
    async def setup_dashboard_data(self, db_session, test_user, async_session):
        """Set up test data for dashboard tests."""
        from services.async_dashboard_service import AsyncDashboardService

        # Create projects
        projects = []
        for i in range(3):
            project = Project(
                name=f"Project {i}",
                description=f"Description {i}",
                owner_id=test_user.id,
                is_active=True,
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
                    type=TaskType.FEATURE,
                )
                db_session.add(task)
                tasks.append(task)

        db_session.commit()

        return {
            "user": test_user,
            "projects": projects,
            "tasks": tasks,
            "service": AsyncDashboardService(async_session),
        }

    @pytest.mark.asyncio
    async def test_get_overview_stats(self, db_session, setup_dashboard_data):
        """Test getting dashboard overview statistics."""
        data = await setup_dashboard_data
        service = data["service"]
        user = data["user"]

        stats = await service.get_overview_stats(user.id)

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

    @pytest.mark.asyncio
    async def test_get_overview_stats_empty(self, db_session, test_user, async_dashboard_service):
        """Test overview stats with no data."""
        stats = await async_dashboard_service.get_overview_stats(test_user.id)

        assert stats is not None
        assert stats["totalProjects"] == 0
        assert stats["totalTasks"] == 0

    @pytest.mark.asyncio
    async def test_get_recent_projects(self, db_session, setup_dashboard_data):
        """Test getting recent projects."""
        data = await setup_dashboard_data
        service = data["service"]
        user = data["user"]

        projects = await service.get_recent_projects(user.id, limit=5)

        assert len(projects) == 3

        for project in projects:
            assert "id" in project
            assert "name" in project
            assert "progress" in project

    @pytest.mark.asyncio
    async def test_get_recent_projects_limit(self, db_session, setup_dashboard_data):
        """Test recent projects with limit."""
        data = await setup_dashboard_data
        service = data["service"]
        user = data["user"]

        projects = await service.get_recent_projects(user.id, limit=2)

        assert len(projects) == 2

    @pytest.mark.asyncio
    async def test_get_recent_activities(self, db_session, setup_dashboard_data, test_user):
        """Test getting recent activities."""
        data = await setup_dashboard_data
        service = data["service"]
        user = data["user"]
        tasks = data["tasks"]

        # Create some task history entries
        for task in tasks[:3]:
            history = TaskHistory(
                task_id=task.id,
                project_id=task.project_id,
                user_id=user.id,
                activity_type=ActivityType.TASK_CREATED,
                description=f"Created task: {task.title}",
            )
            db_session.add(history)

        db_session.commit()

        activities = await service.get_recent_activities(user.id, limit=10)

        assert len(activities) >= 3

    @pytest.mark.asyncio
    async def test_get_recent_activities_empty(
        self, db_session, test_user, async_dashboard_service
    ):
        """Test recent activities with no data."""
        activities = await async_dashboard_service.get_recent_activities(test_user.id)

        assert activities == [] or len(activities) == 0
