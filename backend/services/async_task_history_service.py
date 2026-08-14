"""
Async Service for managing task history and activities.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

import json
import uuid
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.task_history import ActivityType, TaskHistory
from utils.logger import setup_logger

logger = setup_logger("async_task_history_service")
MAX_BATCH_ACTIVITY_ROWS = 1_000


class AsyncTaskHistoryService:
    """Async Service for task history operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_activity(
        self,
        activity_type: ActivityType,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        task_id: uuid.UUID | None = None,
        task_title: str | None = None,
        description: str | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> TaskHistory:
        """
        Create a new activity record.
        """
        logger.debug(
            f"Creating activity: {activity_type}, project_id: {project_id}, user_id: {user_id}"
        )

        activity = TaskHistory(
            activity_type=activity_type,
            project_id=project_id,
            task_id=task_id,
            user_id=user_id,
            task_title=task_title,
            description=description,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
        )

        self.db.add(activity)

        try:
            if commit:
                await self.db.commit()
                await self.db.refresh(activity)
            else:
                await self.db.flush()
            logger.debug(f"Activity created with ID: {activity.id}")
            return activity
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error created activity: {e}")
            raise ValueError(f"Failed to create activity: {e!s}")

    async def get_recent_activities(
        self,
        project_id: uuid.UUID,
        limit: int = 10,
        activity_types: list[ActivityType] | None = None,
    ) -> list[TaskHistory]:
        """
        Get recent activities for a project.
        """
        query = select(TaskHistory).filter(TaskHistory.project_id == project_id)

        if activity_types:
            query = query.filter(TaskHistory.activity_type.in_(activity_types))

        result = await self.db.execute(
            query.order_by(TaskHistory.timestamp.desc(), TaskHistory.id.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_activities_for_projects(
        self,
        project_ids: list[uuid.UUID],
        limit: int = 20,
        activity_types: list[ActivityType] | None = None,
        per_project_limit: int | None = None,
    ) -> list[TaskHistory]:
        """
        Get recent activities for multiple projects.
        Optimized for batch fetching to avoid N+1 queries. When
        ``per_project_limit`` is supplied, use a window function so a large
        project cannot consume the entire global result set.
        """
        if not project_ids:
            return []

        if per_project_limit is not None:
            ranked_history = select(
                TaskHistory.id.label("history_id"),
                func.row_number()
                .over(
                    partition_by=TaskHistory.project_id,
                    order_by=(TaskHistory.timestamp.desc(), TaskHistory.id.desc()),
                )
                .label("project_row_number"),
            ).filter(TaskHistory.project_id.in_(project_ids))
            if activity_types:
                ranked_history = ranked_history.filter(
                    TaskHistory.activity_type.in_(activity_types)
                )

            ranked_subquery = ranked_history.subquery()
            query = (
                select(TaskHistory)
                .join(ranked_subquery, TaskHistory.id == ranked_subquery.c.history_id)
                .filter(ranked_subquery.c.project_row_number <= per_project_limit)
                .order_by(TaskHistory.timestamp.desc(), TaskHistory.id.desc())
                .limit(min(per_project_limit * len(project_ids), MAX_BATCH_ACTIVITY_ROWS))
            )
        else:
            query = select(TaskHistory).filter(TaskHistory.project_id.in_(project_ids))

            if activity_types:
                query = query.filter(TaskHistory.activity_type.in_(activity_types))

            query = query.order_by(TaskHistory.timestamp.desc(), TaskHistory.id.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_recent_activities_paginated(
        self,
        project_id: uuid.UUID,
        limit: int = 20,
        before_id: uuid.UUID | None = None,
        activity_types: list[ActivityType] | None = None,
    ) -> list[TaskHistory]:
        """
        Get recent activities using cursor-based pagination for high performance on large datasets.
        """
        query = select(TaskHistory).filter(TaskHistory.project_id == project_id)

        if before_id:
            cursor_result = await self.db.execute(
                select(TaskHistory.timestamp, TaskHistory.id).filter(TaskHistory.id == before_id)
            )
            cursor = cursor_result.first()
            if cursor:
                cursor_timestamp, cursor_task_id = cursor
                query = query.filter(
                    or_(
                        TaskHistory.timestamp < cursor_timestamp,
                        and_(
                            TaskHistory.timestamp == cursor_timestamp,
                            TaskHistory.id < cursor_task_id,
                        ),
                    )
                )

        if activity_types:
            query = query.filter(TaskHistory.activity_type.in_(activity_types))

        result = await self.db.execute(
            query.order_by(TaskHistory.timestamp.desc(), TaskHistory.id.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def log_project_updated(
        self,
        project_id: uuid.UUID,
        updated_by: uuid.UUID,
        changes: dict[str, Any],
        *,
        commit: bool = True,
    ) -> TaskHistory:
        """
        Log project update activity.
        """
        return await self.create_activity(
            activity_type=ActivityType.PROJECT_UPDATED,
            project_id=project_id,
            user_id=updated_by,
            description="Updated project information",
            new_values=changes,
            commit=commit,
        )

    async def log_project_member_added(
        self,
        project_id: uuid.UUID,
        member_name: str,
        added_by: uuid.UUID,
        *,
        commit: bool = True,
    ) -> TaskHistory:
        """
        Log project member addition activity.
        """
        return await self.create_activity(
            activity_type=ActivityType.PROJECT_MEMBER_ADDED,
            project_id=project_id,
            user_id=added_by,
            description=f"Added {member_name} to project",
            new_values={"member_name": member_name},
            commit=commit,
        )

    async def log_project_member_removed(
        self,
        project_id: uuid.UUID,
        member_name: str,
        removed_by: uuid.UUID,
        *,
        commit: bool = True,
    ) -> TaskHistory:
        """
        Log project member removal activity.
        """
        return await self.create_activity(
            activity_type=ActivityType.PROJECT_MEMBER_REMOVED,
            project_id=project_id,
            user_id=removed_by,
            description=f"Removed {member_name} from project",
            old_values={"member_name": member_name},
            commit=commit,
        )

    async def log_project_member_role_changed(
        self,
        project_id: uuid.UUID,
        member_name: str,
        new_role: str,
        changed_by: uuid.UUID,
        *,
        commit: bool = True,
    ) -> TaskHistory:
        """
        Log project member role change activity.
        """
        return await self.create_activity(
            activity_type=ActivityType.PROJECT_MEMBER_ROLE_CHANGED,
            project_id=project_id,
            user_id=changed_by,
            description=f"Changed {member_name}'s role to {new_role}",
            new_values={"member_name": member_name, "new_role": new_role},
            commit=commit,
        )

    async def log_task_created(
        self, task: Any, created_by: uuid.UUID, *, commit: bool = True
    ) -> TaskHistory:
        """Log task creation."""
        return await self.create_activity(
            activity_type=ActivityType.TASK_CREATED,
            project_id=task.project_id,
            user_id=created_by,
            task_id=task.id,
            task_title=task.title,
            description="Created task",
            new_values={
                "status": task.status.value if hasattr(task.status, "value") else task.status
            },
            commit=commit,
        )

    async def log_task_assigned(
        self,
        task: Any,
        assignee_id: uuid.UUID,
        assigned_by: uuid.UUID,
        *,
        commit: bool = True,
    ) -> TaskHistory:
        """Log task assignment."""
        return await self.create_activity(
            activity_type=ActivityType.TASK_ASSIGNED,
            project_id=task.project_id,
            user_id=assigned_by,
            task_id=task.id,
            task_title=task.title,
            description=f"Assigned task to user {assignee_id}",
            new_values={"assignee_id": str(assignee_id)},
            commit=commit,
        )

    async def log_task_updated(
        self,
        task: Any,
        updated_by: uuid.UUID,
        old_values: dict[str, Any],
        new_values: dict[str, Any],
        *,
        commit: bool = True,
    ) -> TaskHistory:
        """Log task update."""
        return await self.create_activity(
            activity_type=ActivityType.TASK_UPDATED,
            project_id=task.project_id,
            user_id=updated_by,
            task_id=task.id,
            task_title=task.title,
            description="Updated task details",
            old_values=old_values,
            new_values=new_values,
            commit=commit,
        )

    async def log_task_completed(
        self, task: Any, completed_by: uuid.UUID, *, commit: bool = True
    ) -> TaskHistory:
        """Log task completion."""
        return await self.create_activity(
            activity_type=ActivityType.TASK_COMPLETED,
            project_id=task.project_id,
            user_id=completed_by,
            task_id=task.id,
            task_title=task.title,
            description="Completed task",
            new_values={"status": "DONE"},
            commit=commit,
        )

    async def log_task_deleted(
        self, task: Any, deleted_by: uuid.UUID, *, commit: bool = True
    ) -> TaskHistory:
        """Log task deletion."""
        return await self.create_activity(
            activity_type=ActivityType.TASK_DELETED,
            project_id=task.project_id,
            user_id=deleted_by,
            task_id=task.id,
            task_title=task.title,
            description="Deleted task",
            old_values={"title": task.title},
            commit=commit,
        )
