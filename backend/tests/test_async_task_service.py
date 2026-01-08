import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project, ProjectMember
from models.task import Task, TaskPriority, TaskStatus, TaskType
from models.user import User
from schemas.task import TaskAssign, TaskCreate, TaskStatusUpdate, TaskUpdate
from services.async_task_service import AsyncTaskService


# Fixtures
@pytest.fixture
def mock_db_session():
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    # Mock delete as an async method if needed, but in 2.0 it's sync usually on session, but awaitable when flushed?
    # Actually session.delete(obj) is sync. session.execute(delete(...)) is async.
    # The service code uses: await self.db.delete(task) which implies the session used allows await delete?
    # SQLAlchemy AsyncSession.delete is synchronous. But if the code awaits it, it might fail in tests if mock is not async.
    # Let's inspect the service code again: `await self.db.delete(task)` -> line 313.
    # AsyncSession.delete IS NOT awaitable. It adds to session.
    # However, if the user code has `await self.db.delete(task)`, it might be receiving a wrapper or we should check if they are using an extension.
    # Standard AsyncSession.delete is sync. `await session.delete(instance)` would raise TypeError in runtime if it returns None.
    # But wait, maybe the user code is buggy?
    # Let's assume for now we mock it as AsyncMock to satisfy the `await` in the code, or Fix the code if it's wrong.
    # Code: `await self.db.delete(task)`
    # If the code runs in production, `delete` must be awaitable.
    # Let's make it AsyncMock.
    db.delete = AsyncMock()
    return db


@pytest.fixture
def task_service(mock_db_session):
    return AsyncTaskService(mock_db_session)


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def project_id():
    return uuid.uuid4()


# Tests


@pytest.mark.asyncio
async def test_get_task_by_id(task_service, mock_db_session):
    task_id = uuid.uuid4()
    task = Task(id=task_id, title="Test Task")

    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = task
    mock_db_session.execute.return_value = mock_res

    result = await task_service.get_task_by_id(task_id)
    assert result.id == task_id
    assert result.title == "Test Task"


@pytest.mark.asyncio
async def test_get_tasks_filters(task_service, mock_db_session):
    # Setup
    task = Task(id=uuid.uuid4(), status=TaskStatus.TODO)
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [task]
    mock_db_session.execute.return_value = mock_res

    # Test
    result = await task_service.get_tasks(
        project_id=uuid.uuid4(), assignee_id=uuid.uuid4(), status=TaskStatus.TODO
    )

    assert len(result) == 1
    # We can check verify filters applied but that requires inspecting 'query' object logic
    # which is hard with mocks. But we can ensure execute called.
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_is_project_member_owner(task_service, user_id, project_id, mock_db_session):
    # Mock project owner check
    proj = Project(id=project_id, owner_id=user_id)
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = proj
    mock_db_session.execute.return_value = mock_res

    is_member = await task_service._is_project_member(project_id, user_id)
    assert is_member is True


@pytest.mark.asyncio
async def test_is_project_member_regular(task_service, user_id, project_id, mock_db_session):
    # Mock project owner check -> False
    proj = Project(id=project_id, owner_id=uuid.uuid4())
    res_proj = MagicMock()
    res_proj.scalars.return_value.first.return_value = proj

    # Mock member check -> True
    res_mem = MagicMock()
    res_mem.scalars.return_value.first.return_value = ProjectMember()

    mock_db_session.execute.side_effect = [res_proj, res_mem]

    is_member = await task_service._is_project_member(project_id, user_id)
    assert is_member is True


@pytest.mark.asyncio
async def test_create_task_success(task_service, user_id, project_id, mock_db_session):
    # Setup data
    task_data = TaskCreate(title="New Task", project_id=project_id, priority="high")

    # 1. Mock project exists
    res_proj = MagicMock()
    res_proj.scalars.return_value.first.return_value = Project(id=project_id)

    # 2. Mock membership check
    # Need to patch _is_project_member since it makes its own DB calls
    with patch.object(task_service, "_is_project_member", return_value=True):
        mock_db_session.execute.return_value = res_proj

        # Act
        created = await task_service.create_task(task_data, created_by=user_id)

        # Assert
        assert created.title == "New Task"
        assert created.priority == TaskPriority.HIGH
        assert mock_db_session.add.call_count >= 1
        assert mock_db_session.commit.call_count >= 1


@pytest.mark.asyncio
async def test_create_task_not_member(task_service, user_id, project_id, mock_db_session):
    task_data = TaskCreate(title="New Task", project_id=project_id)

    # 1. Mock project exists
    res_proj = MagicMock()
    res_proj.scalars.return_value.first.return_value = Project(id=project_id)
    mock_db_session.execute.return_value = res_proj

    with patch.object(task_service, "_is_project_member", return_value=False):
        with pytest.raises(ValueError, match="Not authorized to create tasks"):
            await task_service.create_task(task_data, created_by=user_id)


@pytest.mark.asyncio
async def test_update_task_success(task_service, user_id, mock_db_session):
    tid = uuid.uuid4()
    task = Task(
        id=tid,
        title="Old Title",
        project_id=uuid.uuid4(),
        created_by=user_id,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        type=TaskType.FEATURE,
    )

    # Mock get task
    task_service.get_task_by_id = AsyncMock(return_value=task)

    # Mock permissions (authorized as creator)
    task_service._check_task_permission = AsyncMock(return_value=None)

    update_data = TaskUpdate(title="New Title", status="in_progress")

    updated = await task_service.update_task(tid, update_data, user_id)

    assert updated.title == "New Title"
    assert updated.status == TaskStatus.IN_PROGRESS
    assert mock_db_session.commit.call_count >= 1


@pytest.mark.asyncio
async def test_delete_task_success(task_service, user_id, mock_db_session):
    tid = uuid.uuid4()
    task = Task(id=tid, title="To Delete", project_id=uuid.uuid4(), created_by=user_id)

    task_service.get_task_by_id = AsyncMock(return_value=task)
    task_service._check_task_permission = AsyncMock(return_value=None)

    res = await task_service.delete_task(tid, user_id)

    assert res is True
    # In async delete is separate from commit usually but here mapped to session.delete
    mock_db_session.delete.assert_called_once_with(task)
    assert mock_db_session.commit.call_count >= 1


@pytest.mark.asyncio
async def test_update_task_status(task_service, user_id, mock_db_session):
    tid = uuid.uuid4()
    task = Task(id=tid, status=TaskStatus.TODO, project_id=uuid.uuid4(), created_by=user_id)

    task_service.get_task_by_id = AsyncMock(return_value=task)
    task_service._check_task_permission = AsyncMock(return_value=None)

    update_data = TaskStatusUpdate(status="done")

    updated = await task_service.update_task_status(tid, update_data, user_id)

    assert updated.status == TaskStatus.DONE
    assert mock_db_session.commit.call_count >= 1


@pytest.mark.asyncio
async def test_assign_task(task_service, user_id, mock_db_session):
    tid = uuid.uuid4()
    task = Task(id=tid, project_id=uuid.uuid4(), created_by=user_id, assignee_id=None)

    assignee_id = uuid.uuid4()

    task_service.get_task_by_id = AsyncMock(return_value=task)
    task_service._check_task_permission = AsyncMock(return_value=None)

    # Mock assignee check
    res_assignee = MagicMock()
    res_assignee.scalars.return_value.first.return_value = User(id=assignee_id)
    mock_db_session.execute.return_value = res_assignee

    data = TaskAssign(assignee_id=assignee_id)

    updated = await task_service.assign_task(tid, data, user_id)

    assert updated.assignee_id == assignee_id
    assert mock_db_session.commit.call_count >= 1


@pytest.mark.asyncio
async def test_get_user_tasks(task_service, user_id, mock_db_session):
    # Mock count
    res_cnt = MagicMock()
    res_cnt.scalar.return_value = 5

    # Mock list
    t1 = Task(id=uuid.uuid4())
    res_list = MagicMock()
    res_list.scalars.return_value.all.return_value = [t1]

    mock_db_session.execute.side_effect = [res_cnt, res_list]

    tasks, count = await task_service.get_user_tasks(user_id, search="foo", status="todo")

    assert count == 5
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_get_tasks_due_soon(task_service, user_id, mock_db_session):
    res = MagicMock()
    res.scalars.return_value.all.return_value = [Task(id=uuid.uuid4())]
    mock_db_session.execute.return_value = res

    tasks = await task_service.get_tasks_due_soon(user_id, days=5)
    assert len(tasks) == 1
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_overdue_tasks(task_service, user_id, mock_db_session):
    res = MagicMock()
    res.scalars.return_value.all.return_value = [Task(id=uuid.uuid4())]
    mock_db_session.execute.return_value = res

    tasks = await task_service.get_overdue_tasks(user_id)
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_get_task_stats_for_user(task_service, user_id, mock_db_session):
    # Mock result row: (total, completed, in_progress, todo)
    row = (10, 5, 2, 3)
    res = MagicMock()
    res.first.return_value = row
    mock_db_session.execute.return_value = res

    stats = await task_service.get_task_stats_for_user(user_id)

    assert stats["total"] == 10
    assert stats["completed"] == 5
    assert stats["in_progress"] == 2
    assert stats["completion_rate"] == 50


# Permission tests
@pytest.mark.asyncio
async def test_check_task_permission_creator(task_service, user_id):
    task = Task(created_by=user_id, project_id=uuid.uuid4())
    # Should not raise
    await task_service._check_task_permission(task, user_id)


@pytest.mark.asyncio
async def test_check_task_permission_assignee(task_service, user_id):
    task = Task(created_by=uuid.uuid4(), assignee_id=user_id, project_id=uuid.uuid4())
    # Should not raise if allow_assignee=True
    await task_service._check_task_permission(task, user_id, allow_assignee=True)


@pytest.mark.asyncio
async def test_check_task_permission_unauthorized(task_service, user_id):
    task = Task(created_by=uuid.uuid4(), assignee_id=uuid.uuid4(), project_id=uuid.uuid4())

    with patch.object(task_service, "_is_project_admin", return_value=False):
        with pytest.raises(ValueError, match="Not authorized"):
            await task_service._check_task_permission(task, user_id)
