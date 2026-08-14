import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.async_task_history_service import AsyncTaskHistoryService


@pytest.mark.asyncio
async def test_batch_activity_query_caps_each_project_before_global_limit():
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute.return_value = result
    service = AsyncTaskHistoryService(db)

    project_ids = [uuid.uuid4(), uuid.uuid4()]
    await service.get_recent_activities_for_projects(
        project_ids,
        limit=50,
        per_project_limit=50,
    )

    statement = str(db.execute.await_args.args[0]).lower()
    assert "row_number() over" in statement
    assert "partition by task_history.project_id" in statement
    assert "limit" in statement
