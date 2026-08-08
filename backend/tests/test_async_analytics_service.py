import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project
from models.user import User
from services.async_analytics_service import AsyncAnalyticsService


@pytest.fixture
def mock_db_session():
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def analytics_service(mock_db_session):
    return AsyncAnalyticsService(mock_db_session)


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def project_ids():
    return [uuid.uuid4(), uuid.uuid4()]


@pytest.mark.asyncio
async def test_get_analytics_overview_cached(analytics_service, user_id):
    # Mock cache hit
    with patch("services.cache_service.cache_service.get", return_value={"overview": "cached"}):
        result = await analytics_service.get_analytics_overview(user_id)
        assert result == {"overview": "cached"}
        # Ensure DB not called
        analytics_service.db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_analytics_overview_no_projects(analytics_service, user_id):
    # Mock cache miss
    with (
        patch("services.cache_service.cache_service.get", return_value=None),
        patch("services.cache_service.cache_service.set", new_callable=AsyncMock) as cache_set,
    ):
        # Mock total projects count = 0
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = 0
        analytics_service.db.execute.return_value = mock_scalar

        result = await analytics_service.get_analytics_overview(user_id)
        assert result["overview"]["totalProjects"] == 0
        assert result["projects"] == []
        cache_set.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_analytics_overview_success(analytics_service, user_id, project_ids):
    # Mock cache miss
    with (
        patch("services.cache_service.cache_service.get", return_value=None),
        patch.object(
            analytics_service, "_get_overview_metrics", return_value={"totalProjects": 2}
        ) as mock_overview,
        patch.object(
            analytics_service, "_get_project_stats", return_value=[{"name": "P1"}]
        ) as mock_proj_stats,
        patch.object(
            analytics_service,
            "_get_team_stats",
            return_value=[{"name": "U1", "avatar": None, "tasks": 3}],
        ),
        patch.object(analytics_service, "_get_trends", return_value=[{"metric": "Tasks"}]),
        patch.object(
            analytics_service,
            "_get_distributions",
            return_value={
                "status": [],
                "priority": [],
                "workload": [],
                "workloadTotal": 0,
            },
        ),
        patch.object(
            analytics_service,
            "_get_daily_trends",
            return_value=[{"date": "Jan 1", "created": 0, "completed": 0}],
        ),
    ):
        # Mock total projects count > 0
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = 2
        analytics_service.db.execute.return_value = mock_scalar

        result = await analytics_service.get_analytics_overview(user_id)

        assert result["overview"]["totalProjects"] == 2
        assert len(result["projects"]) == 1
        assert len(result["team"]) == 1
        assert len(result["trends"]) == 1
        assert result["teamWorkloadTotal"] == 0

        # Verify calls
        mock_overview.assert_called_once()
        mock_proj_stats.assert_called_once()


@pytest.mark.asyncio
async def test_get_overview_metrics(analytics_service, user_id, project_ids):
    # Mock task stats (total, completed, in_progress, overdue)
    res_tasks = MagicMock()
    res_tasks.first.return_value = (10, 5, 3, 2)

    # Mock combined active project and member counts
    res_counts = MagicMock()
    res_counts.first.return_value = (1, 4)

    analytics_service.db.execute.side_effect = [res_tasks, res_counts]

    metrics = await analytics_service._get_overview_metrics(project_ids, user_id, total_projects=2)

    assert metrics["activeProjects"] == 1
    assert metrics["totalTasks"] == 10
    assert metrics["completedTasks"] == 5
    assert metrics["teamMembers"] == 4
    assert metrics["completionRate"] == 50.0


@pytest.mark.asyncio
async def test_get_project_stats(analytics_service, project_ids):
    # Mock project stats
    # rows: (Project, task_count, completed)
    p1 = Project(id=project_ids[0], name="P1")
    row1 = (p1, 10, 8)

    res = MagicMock()
    res.all.return_value = [row1]
    analytics_service.db.execute.return_value = res

    stats = await analytics_service._get_project_stats(project_ids)

    assert len(stats) == 1
    assert stats[0]["name"] == "P1"
    assert stats[0]["progress"] == 80
    assert stats[0]["velocity"] == "high"


@pytest.mark.asyncio
async def test_get_team_stats(analytics_service, project_ids):
    # Mock team stats
    # rows: (User, total, completed)
    u1 = User(id=uuid.uuid4(), name="U1", avatar_url="url")
    row1 = (u1, 10, 5)

    res = MagicMock()
    res.all.return_value = [row1]
    analytics_service.db.execute.return_value = res

    stats = await analytics_service._get_team_stats(project_ids)

    assert len(stats) == 1
    assert stats[0]["name"] == "U1"
    assert stats[0]["efficiency"] == 50


@pytest.mark.asyncio
async def test_get_trends(analytics_service, project_ids):
    # Mock DB counts: current_completed, previous_completed
    res_curr = MagicMock()
    res_curr.scalar.return_value = 20

    res_prev = MagicMock()
    res_prev.scalar.return_value = 10

    analytics_service.db.execute.side_effect = [res_curr, res_prev]

    trends = await analytics_service._get_trends(project_ids, days=30)

    assert len(trends) == 2
    # Task completion change: (20-10)/10 * 100 = 100%
    assert trends[0]["change"] == 100.0


@pytest.mark.asyncio
async def test_get_daily_trends(analytics_service, project_ids):
    # Mock daily counts
    today_str = str(datetime.now(UTC).date())
    res_created = MagicMock()
    res_created.all.return_value = [(today_str, 5)]

    res_completed = MagicMock()
    res_completed.all.return_value = [(today_str, 3)]

    analytics_service.db.execute.side_effect = [res_created, res_completed]

    trends = await analytics_service._get_daily_trends(project_ids, days=7)

    assert len(trends) == 7
    # Find today
    today_trend = next(t for t in trends if t["fullDate"] == today_str)
    assert today_trend["created"] == 5
    assert today_trend["completed"] == 3


@pytest.mark.asyncio
async def test_get_distributions(analytics_service, project_ids):
    res_workload_total = MagicMock()
    res_workload_total.scalar.return_value = 1

    res_status = MagicMock()
    res_status.all.return_value = [("done", 10), ("todo", 5)]

    res_priority = MagicMock()
    res_priority.all.return_value = [("high", 8), ("low", 7)]

    u1 = User(id=uuid.uuid4(), name="U1")
    res_workload = MagicMock()
    res_workload.all.return_value = [(u1, 15)]

    analytics_service.db.execute.side_effect = [
        res_status,
        res_priority,
        res_workload_total,
        res_workload,
    ]

    dists = await analytics_service._get_distributions(project_ids, workload_limit=10)

    assert len(dists["status"]) == 2
    assert len(dists["priority"]) == 2
    assert len(dists["workload"]) == 1
    assert dists["workload"][0]["tasks"] == 15
    assert dists["workloadTotal"] == 1


@pytest.mark.asyncio
async def test_get_project_analytics(analytics_service):
    pid = uuid.uuid4()

    # Task stats
    res_stats = MagicMock()
    res_stats.first.return_value = (100, 50, 30, 20)

    # Member count
    res_members = MagicMock()
    res_members.scalar.return_value = 5

    analytics_service.db.execute.side_effect = [res_stats, res_members]

    result = await analytics_service.get_project_analytics(pid)

    assert result["task_stats"]["total"] == 100
    assert result["member_count"] == 5
    assert result["completion_rate"] == 50


@pytest.mark.asyncio
async def test_get_team_workload_paginated(analytics_service, user_id):
    # Total count
    res_count = MagicMock()
    res_count.scalar.return_value = 1

    # Stats rows
    res_stats = MagicMock()
    uid = uuid.uuid4()
    res_stats.all.return_value = [(uid, "U1", None, 10, 5)]

    analytics_service.db.execute.side_effect = [res_count, res_stats]

    result = await analytics_service.get_team_workload_paginated(user_id)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["name"] == "U1"
    assert result["items"][0]["progress"] == 50
    assert result["page_size"] == 10
    assert result["total_pages"] == 1
    assert result["has_next"] is False
    assert result["has_prev"] is False


@pytest.mark.asyncio
async def test_get_project_productivity(analytics_service):
    pid = uuid.uuid4()

    # Completions
    res = MagicMock()
    today_date = datetime.now(UTC).date()
    res.all.return_value = [(today_date, 5)]
    analytics_service.db.execute.return_value = res

    result = await analytics_service.get_project_productivity(pid)

    assert result["totalCompleted"] == 5
    assert len(result["data"]) == 1
    assert result["data"][0]["completed"] == 5


@pytest.mark.asyncio
async def test_get_project_contributions(analytics_service):
    pid = uuid.uuid4()

    # Stats
    uid = uuid.uuid4()
    res_stats = MagicMock()
    res_stats.all.return_value = [(uid, 20, 10)]

    # Users
    u1 = User(id=uid, name="U1")
    res_users = MagicMock()
    res_users.scalars.return_value.all.return_value = [u1]

    analytics_service.db.execute.side_effect = [res_stats, res_users]

    result = await analytics_service.get_project_contributions(pid)

    assert result["totalTasks"] == 20
    assert result["totalCompleted"] == 10
    assert len(result["contributors"]) == 1
    assert (
        result["contributors"][0]["percentage"] == 100
    )  # 20/20 tasks of total found (if only 1 user) or 0?
    # Logic: round(user_tasks / total_tasks * 100)
    # total_tasks calculated in loop = 20. user_tasks = 20. 20/20*100 = 100.
