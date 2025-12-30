"""
Async Unit tests for AsyncTaskService.
"""
import pytest
import uuid
from models.task import Task, TaskStatus, TaskPriority, TaskType
from models.project import Project, ProjectMember, MemberRole
from models.user import User
from schemas.task import TaskCreate, TaskUpdate, TaskStatusUpdate


class TestAsyncTaskService:
    """Test cases for AsyncTaskService."""

    @pytest.fixture
    async def setup_task_data(self, db_session, test_user, async_session):
        """Create a project and test data for task tests."""
        from services.async_task_service import AsyncTaskService
        
        # Create a project for tasks
        project = Project(
            name="Test Project",
            description="A test project",
            owner_id=test_user.id,
            is_active=True
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)
        
        # Add user as project member (OWNER)
        member = ProjectMember(
            project_id=project.id,
            user_id=test_user.id,
            role=MemberRole.OWNER.value
        )
        db_session.add(member)
        db_session.commit()
        
        return {
            "project": project,
            "user": test_user,
            "service": AsyncTaskService(async_session)
        }

    @pytest.mark.asyncio
    async def test_create_task_success(self, db_session, setup_task_data):
        """Test successful task creation."""
        data = await setup_task_data
        service = data["service"]
        project = data["project"]
        user = data["user"]
        
        task_data = TaskCreate(
            title="Test Task",
            description="Test description",
            project_id=project.id,
            priority="medium",
            type="feature"
        )
        
        task = await service.create_task(task_data, user.id)
        
        assert task is not None
        assert task.title == "Test Task"
        assert task.description == "Test description"
        assert task.project_id == project.id
        assert task.created_by == user.id
        assert task.status == TaskStatus.TODO

    @pytest.mark.asyncio
    async def test_create_task_with_assignee(self, db_session, setup_task_data):
        """Test task creation with assignee."""
        data = await setup_task_data
        service = data["service"]
        project = data["project"]
        user = data["user"]
        
        task_data = TaskCreate(
            title="Assigned Task",
            description="Task with assignee",
            project_id=project.id,
            priority="high",
            type="bug",
            assignee_id=user.id
        )
        
        task = await service.create_task(task_data, user.id)
        
        assert task.assignee_id == user.id

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, db_session, setup_task_data):
        """Test getting task by ID."""
        data = await setup_task_data
        service = data["service"]
        project = data["project"]
        user = data["user"]
        
        # Create a task first
        task_data = TaskCreate(
            title="Task to Retrieve",
            project_id=project.id,
            priority="low"
        )
        created_task = await service.create_task(task_data, user.id)
        
        # Retrieve it
        retrieved_task = await service.get_task_by_id(created_task.id)
        
        assert retrieved_task is not None
        assert retrieved_task.id == created_task.id
        assert retrieved_task.title == "Task to Retrieve"

    @pytest.mark.asyncio
    async def test_get_task_by_id_not_found(self, db_session, setup_task_data):
        """Test getting non-existent task."""
        data = await setup_task_data
        service = data["service"]
        
        fake_id = uuid.uuid4()
        task = await service.get_task_by_id(fake_id)
        
        assert task is None

    @pytest.mark.asyncio
    async def test_update_task_success(self, db_session, setup_task_data):
        """Test successful task update."""
        data = await setup_task_data
        service = data["service"]
        project = data["project"]
        user = data["user"]
        
        # Create a task
        task_data = TaskCreate(
            title="Original Title",
            project_id=project.id,
            priority="low"
        )
        task = await service.create_task(task_data, user.id)
        
        # Update it
        update_data = TaskUpdate(
            title="Updated Title",
            description="New description",
            priority="high"
        )
        updated_task = await service.update_task(task.id, update_data, user.id)
        
        assert updated_task.title == "Updated Title"
        assert updated_task.description == "New description"
        assert updated_task.priority == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, db_session, setup_task_data):
        """Test updating non-existent task."""
        data = await setup_task_data
        service = data["service"]
        user = data["user"]
        
        fake_id = uuid.uuid4()
        update_data = TaskUpdate(title="New Title")
        
        with pytest.raises(ValueError, match="not found"):
            await service.update_task(fake_id, update_data, user.id)

    @pytest.mark.asyncio
    async def test_delete_task_success(self, db_session, setup_task_data):
        """Test successful task deletion."""
        data = await setup_task_data
        service = data["service"]
        project = data["project"]
        user = data["user"]
        
        # Create a task
        task_data = TaskCreate(
            title="Task to Delete",
            project_id=project.id,
            priority="low"
        )
        task = await service.create_task(task_data, user.id)
        task_id = task.id
        
        # Delete it
        result = await service.delete_task(task_id, user.id)
        
        assert result is True
        assert await service.get_task_by_id(task_id) is None

    @pytest.mark.asyncio
    async def test_update_task_status(self, db_session, setup_task_data):
        """Test updating task status."""
        data = await setup_task_data
        service = data["service"]
        project = data["project"]
        user = data["user"]
        
        # Create a task
        task_data = TaskCreate(
            title="Status Test Task",
            project_id=project.id,
            priority="medium"
        )
        task = await service.create_task(task_data, user.id)
        assert task.status == TaskStatus.TODO
        
        # Update status
        status_update = TaskStatusUpdate(status="in_progress")
        updated_task = await service.update_task_status(task.id, status_update, user.id)
        
        assert updated_task.status == TaskStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_get_project_tasks(self, db_session, setup_task_data):
        """Test getting tasks for a specific project."""
        data = await setup_task_data
        service = data["service"]
        project = data["project"]
        user = data["user"]
        
        # Create tasks in project
        for i in range(3):
            task_data = TaskCreate(
                title=f"Project Task {i}",
                project_id=project.id,
                priority="medium"
            )
            await service.create_task(task_data, user.id)
        
        tasks, total = await service.get_project_tasks(project.id)
        
        assert len(tasks) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_get_user_tasks(self, db_session, setup_task_data):
        """Test getting tasks assigned to or created by user."""
        data = await setup_task_data
        service = data["service"]
        project = data["project"]
        user = data["user"]
        
        # Create tasks assigned to user
        for i in range(2):
            task_data = TaskCreate(
                title=f"User Task {i}",
                project_id=project.id,
                priority="medium",
                assignee_id=user.id
            )
            await service.create_task(task_data, user.id)
        
        tasks, total = await service.get_user_tasks(user.id)
        
        assert total >= 2
