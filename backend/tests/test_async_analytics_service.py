import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project
from models.user import User
from schemas.analytics import AnalyticsOverviewMetrics, AnalyticsOverviewResponse
from services.async_analytics_service import (
    AnalyticsRefreshInProgressError,
    AsyncAnalyticsService,
)


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
async def test_get_analytics_overview_coalesces_concurrent_cache_misses(user_id):
    first_db = AsyncMock(spec=AsyncSession)
    second_db = AsyncMock(spec=AsyncSession)
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    first_db.execute.return_value = count_result
    second_db.execute.return_value = count_result
    first_service = AsyncAnalyticsService(first_db)
    second_service = AsyncAnalyticsService(second_db)

    cache_store: dict[str, dict[str, object]] = {}
    overview_calls = 0

    async def cache_get(key: str):
        return cache_store.get(key)

    async def cache_set(key: str, value: dict[str, object], ttl: int):
        cache_store[key] = value

    async def build_overview(*_args, **_kwargs):
        nonlocal overview_calls
        overview_calls += 1
        await asyncio.sleep(0.01)
        return {"totalProjects": 1}

    with (
        patch("services.async_analytics_service.cache_service.get", side_effect=cache_get),
        patch("services.async_analytics_service.cache_service.set", side_effect=cache_set),
        patch.object(AsyncAnalyticsService, "_get_overview_metrics", side_effect=build_overview),
        patch.object(
            AsyncAnalyticsService,
            "_get_project_stats",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            AsyncAnalyticsService,
            "_get_team_stats",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            AsyncAnalyticsService,
            "_get_trends",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            AsyncAnalyticsService,
            "_get_distributions",
            new_callable=AsyncMock,
            return_value={"status": [], "priority": [], "workload": [], "workloadTotal": 0},
        ),
        patch.object(
            AsyncAnalyticsService,
            "_get_daily_trends",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        results = await asyncio.gather(
            first_service.get_analytics_overview(user_id),
            second_service.get_analytics_overview(user_id),
        )

    assert results[0] == results[1]
    assert overview_calls == 1


@pytest.mark.asyncio
async def test_get_analytics_overview_uses_value_populated_by_other_worker(
    analytics_service, user_id
):
    cache_values = [None, None, {"overview": "worker-result"}]

    async def cache_get(_key: str):
        return cache_values.pop(0)

    with (
        patch("services.async_analytics_service.cache_service.get", side_effect=cache_get),
        patch(
            "services.async_analytics_service.cache_service.try_acquire_distributed_lock",
            new_callable=AsyncMock,
            return_value=False,
        ) as acquire_lock,
        patch(
            "services.async_analytics_service.cache_service.release_distributed_lock",
            new_callable=AsyncMock,
        ) as release_lock,
        patch("services.async_analytics_service.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await analytics_service.get_analytics_overview(user_id)

    assert result == {"overview": "worker-result"}
    acquire_lock.assert_awaited_once()
    release_lock.assert_not_awaited()
    analytics_service.db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_analytics_overview_does_not_duplicate_another_worker_build(
    analytics_service, user_id
):
    with (
        patch("services.async_analytics_service.cache_service.get", return_value=None),
        patch(
            "services.async_analytics_service.cache_service.try_acquire_distributed_lock",
            new_callable=AsyncMock,
            side_effect=[False, False],
        ) as acquire_lock,
        patch("services.async_analytics_service.asyncio.sleep", new_callable=AsyncMock),
        patch.object(
            analytics_service,
            "_build_analytics_overview",
            new_callable=AsyncMock,
        ) as build_overview,
        pytest.raises(AnalyticsRefreshInProgressError),
    ):
        await analytics_service.get_analytics_overview(user_id)

    assert acquire_lock.await_count == 2
    build_overview.assert_not_awaited()


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
    res = MagicMock()
    res.first.return_value = MagicMock(
        _mapping={
            "total_tasks": 10,
            "completed_tasks": 5,
            "in_progress_tasks": 3,
            "overdue_tasks": 2,
            "active_projects": 1,
            "member_count": 4,
        }
    )
    analytics_service.db.execute.return_value = res

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
    assert stats[0]["id"] == str(u1.id)
    assert stats[0]["name"] == "U1"
    assert stats[0]["efficiency"] == 50


@pytest.mark.asyncio
async def test_get_team_stats_falls_back_to_stable_user_identity(analytics_service, project_ids):
    user = User(id=uuid.uuid4(), name=None, username="u1", email="u1@example.com")
    result = MagicMock()
    result.all.return_value = [(user, 1, 0)]
    analytics_service.db.execute.return_value = result

    stats = await analytics_service._get_team_stats(project_ids)

    assert stats[0]["name"] == "u1"


def test_analytics_overview_schema_preserves_workload_total():
    response = AnalyticsOverviewResponse(
        overview=AnalyticsOverviewMetrics(),
        teamWorkloadTotal=12,
    )

    assert response.teamWorkloadTotal == 12


@pytest.mark.asyncio
async def test_get_trends(analytics_service, project_ids):
    res = MagicMock()
    res.first.return_value = MagicMock(current_completed=20, previous_completed=10)
    analytics_service.db.execute.return_value = res

    trends = await analytics_service._get_trends(project_ids, days=30)

    assert len(trends) == 2
    # Task completion change: (20-10)/10 * 100 = 100%
    assert trends[0]["change"] == 100.0


@pytest.mark.asyncio
async def test_get_daily_trends(analytics_service, project_ids):
    today_str = str(datetime.now(UTC).date())
    res = MagicMock()
    res.all.return_value = [
        MagicMock(date=today_str, activity_type="TASK_CREATED", count=5),
        MagicMock(date=today_str, activity_type="TASK_COMPLETED", count=3),
    ]
    analytics_service.db.execute.return_value = res

    trends = await analytics_service._get_daily_trends(project_ids, days=7)

    assert len(trends) == 7
    # Find today
    today_trend = next(t for t in trends if t["fullDate"] == today_str)
    assert today_trend["created"] == 5
    assert today_trend["completed"] == 3


@pytest.mark.asyncio
async def test_get_distributions(analytics_service, project_ids):
    res_distributions = MagicMock()
    res_distributions.all.return_value = [
        ("status", "done", 10),
        ("status", "todo", 5),
        ("priority", "high", 8),
        ("priority", "low", 7),
        ("workload_total", None, 1),
    ]

    u1 = User(id=uuid.uuid4(), name="U1")
    res_workload = MagicMock()
    res_workload.all.return_value = [(u1, 15)]

    analytics_service.db.execute.side_effect = [
        res_distributions,
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
