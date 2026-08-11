"""
Async Dashboard service for analytics and statistics.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import String, and_, case, cast, desc, distinct, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.project import Project, ProjectMember
from models.task import Task, TaskStatus
from models.task_history import ActivityType, TaskHistory
from models.user import User
from services.cache_service import cache_service
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Cache TTL in seconds
DASHBOARD_CACHE_TTL = 120  # 2 minutes


class AsyncDashboardService:
    """Async service class for dashboard operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_accessible_projects_subquery(self, user_id: uuid.UUID):
        """
        Get subquery for projects accessible by the user (owned or member).
        """
        return (
            select(Project.id)
            .outerjoin(ProjectMember, Project.id == ProjectMember.project_id)
            .filter(
                Project.is_active.is_(True),
                or_(Project.owner_id == user_id, ProjectMember.user_id == user_id),
            )
        )

    @staticmethod
    def _get_cached_list(cached: Any) -> list[dict[str, Any]] | None:
        """Normalize a cached list payload or return None on a cache miss."""
        if not isinstance(cached, dict):
            return None
        cached_list = cached.get("_list_data")
        if not isinstance(cached_list, list):
            return None
        return [
            {str(key): value for key, value in item.items()}
            for item in cached_list
            if isinstance(item, dict)
        ]

    @staticmethod
    def _format_recent_project_rows(rows: list) -> list[dict[str, Any]]:
        """Format project aggregate rows for the dashboard API."""
        projects = []
        for project, p_total, p_completed in rows:
            p_total = p_total or 0
            p_completed = p_completed or 0
            progress = round(p_completed / p_total * 100) if p_total > 0 else 0
            projects.append(
                {
                    "id": str(project.id),
                    "name": project.name,
                    "description": project.description,
                    "progress": progress,
                    "color": project.color or "#6366f1",
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                }
            )
        return projects

    @staticmethod
    def _format_recent_activity_row(
        activity: TaskHistory,
        user: User | None,
        project: Project | None,
        task: Task | None,
        action_map: dict[str, str],
    ) -> dict[str, Any]:
        """Format one task-history row for the dashboard API."""
        activity_type = (
            activity.activity_type.value
            if hasattr(activity.activity_type, "value")
            else str(activity.activity_type)
        )
        if task:
            target = task.title
        elif project:
            target = project.name
        else:
            target = "Unknown Target"

        project_info = None
        if project:
            project_info = {
                "name": project.name,
                "id": str(activity.project_id),
            }

        return {
            "id": str(activity.id),
            "user": {
                "name": user.name if user else "Unknown User",
                "id": str(activity.user_id),
                "avatar": user.avatar_url if user else None,
            },
            "action": action_map.get(activity_type, "performed action"),
            "target": target,
            "time": activity.timestamp.isoformat() if activity.timestamp else None,
            "project": project_info,
        }

    @staticmethod
    def _format_recent_activity_rows(rows: Sequence[Any]) -> list[dict[str, Any]]:
        """Format task-history rows for the dashboard API."""
        action_map = {
            "TASK_CREATED": "created task",
            "TASK_UPDATED": "updated task",
            "TASK_COMPLETED": "completed task",
            "TASK_ASSIGNED": "assigned task",
            "TASK_UNASSIGNED": "unassigned task",
            "TASK_DELETED": "deleted task",
            "PROJECT_MEMBER_ADDED": "added member to project",
            "PROJECT_MEMBER_REMOVED": "removed member from project",
            "PROJECT_MEMBER_ROLE_CHANGED": "changed member role in project",
            "PROJECT_UPDATED": "updated project",
            "PROJECT_CREATED": "created project",
        }
        activities = []
        for activity, user, project, task in rows:
            activities.append(
                AsyncDashboardService._format_recent_activity_row(
                    activity, user, project, task, action_map
                )
            )
        return activities

    @staticmethod
    def _overview_metric(values: Any, key: str) -> int:
        """Read an aggregate metric with the query's zero-value fallback."""
        return values[key] or 0

    async def get_overview_stats(self, user_id: uuid.UUID) -> dict[str, Any]:
        """
        Get dashboard overview statistics using optimized async queries.
        Uses caching and pre-materialized project IDs to reduce DB load.
        """
        # B6: Check cache first
        cache_key = f"dashboard:overview:{user_id}"
        cached = await cache_service.get(cache_key)
        if cached:
            logger.debug(f"Serving dashboard overview from cache for user {user_id}")
            return cached

        # B5: Use subquery directly in IN clauses to avoid pre-materializing list and hitting IN clause limits
        accessible_projects_subq = self._get_accessible_projects_subquery(user_id)

        # Time ranges for trends
        now = datetime.now(UTC)
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)

        # Each CTE returns one aggregate row. Selecting them together keeps
        # the three independent aggregates in one database round trip while
        # retaining one AsyncSession for the request.
        project_stats = (
            select(
                func.count(distinct(Project.id)).label("total_projects"),
                func.count(
                    distinct(case((Project.created_at >= thirty_days_ago, Project.id)))
                ).label("projects_created_30d"),
            )
            .filter(Project.id.in_(accessible_projects_subq))
            .cte("dashboard_project_stats")
        )
        task_stats = (
            select(
                func.count(Task.id).label("total_tasks"),
                func.sum(
                    case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)
                ).label("completed_tasks"),
                func.sum(
                    case((cast(Task.status, String) == TaskStatus.IN_PROGRESS.value, 1), else_=0)
                ).label("in_progress_tasks"),
                func.sum(
                    case(
                        (
                            and_(
                                Task.assignee_id == user_id,
                                cast(Task.status, String) == TaskStatus.IN_REVIEW.value,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("pending_review_tasks"),
                func.sum(
                    case(
                        (
                            and_(
                                Task.created_at >= thirty_days_ago,
                                cast(Task.status, String) == TaskStatus.IN_PROGRESS.value,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("new_active_tasks"),
                func.sum(
                    case(
                        (
                            and_(
                                Task.created_at >= thirty_days_ago,
                                cast(Task.status, String) == TaskStatus.DONE.value,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("new_completed_tasks"),
                func.sum(
                    case(
                        (
                            and_(
                                Task.created_at >= thirty_days_ago,
                                Task.assignee_id == user_id,
                                cast(Task.status, String) == TaskStatus.IN_PROGRESS.value,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("my_new_active_tasks"),
                func.sum(
                    case(
                        (
                            and_(
                                Task.created_at >= thirty_days_ago,
                                Task.assignee_id == user_id,
                                cast(Task.status, String) == TaskStatus.DONE.value,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("my_new_completed_tasks"),
            )
            .filter(Task.project_id.in_(accessible_projects_subq))
            .cte("dashboard_task_stats")
        )
        history_stats = (
            select(
                func.sum(
                    case(
                        (
                            and_(
                                cast(TaskHistory.activity_type, String)
                                == ActivityType.TASK_COMPLETED.value,
                                TaskHistory.timestamp >= thirty_days_ago,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("completed_30d"),
                func.sum(
                    case(
                        (
                            and_(
                                TaskHistory.user_id == user_id,
                                cast(TaskHistory.activity_type, String)
                                == ActivityType.TASK_COMPLETED.value,
                                TaskHistory.timestamp >= thirty_days_ago,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("my_completed_30d"),
                func.sum(
                    case(
                        (
                            and_(
                                cast(TaskHistory.activity_type, String)
                                == ActivityType.TASK_COMPLETED.value,
                                TaskHistory.timestamp >= seven_days_ago,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("velocity_7d"),
                func.sum(
                    case(
                        (
                            and_(
                                cast(TaskHistory.activity_type, String)
                                == ActivityType.TASK_COMPLETED.value,
                                TaskHistory.timestamp >= fourteen_days_ago,
                                TaskHistory.timestamp < seven_days_ago,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("velocity_prev_7d"),
            )
            .filter(
                TaskHistory.project_id.in_(accessible_projects_subq),
                TaskHistory.timestamp >= thirty_days_ago,
            )
            .cte("dashboard_history_stats")
        )
        combined_stmt = (
            select(project_stats, task_stats, history_stats)
            .select_from(project_stats)
            .join(task_stats, true())
            .join(history_stats, true())
        )
        combined_result = await self.db.execute(combined_stmt)
        row = combined_result.first()
        if row is None:
            empty_response = self._get_empty_stats_response()
            await cache_service.set(cache_key, empty_response, ttl=DASHBOARD_CACHE_TTL)
            return empty_response

        values = row._mapping
        total_projects = self._overview_metric(values, "total_projects")
        projects_created_last_30_days = self._overview_metric(values, "projects_created_30d")
        if total_projects == 0:
            empty_response = self._get_empty_stats_response()
            await cache_service.set(cache_key, empty_response, ttl=DASHBOARD_CACHE_TTL)
            return empty_response

        total_tasks = self._overview_metric(values, "total_tasks")
        completed_tasks = self._overview_metric(values, "completed_tasks")
        in_progress_tasks = self._overview_metric(values, "in_progress_tasks")
        pending_review_tasks = self._overview_metric(values, "pending_review_tasks")

        # Trends processing
        previous_total_projects = total_projects - projects_created_last_30_days
        projects_change = self._calculate_percentage_change(total_projects, previous_total_projects)

        tasks_completed_last_30_days = self._overview_metric(values, "completed_30d")
        my_completed_last_30_days = self._overview_metric(values, "my_completed_30d")
        team_velocity_val = self._overview_metric(values, "velocity_7d")
        prev_velocity_val = self._overview_metric(values, "velocity_prev_7d")

        new_active_tasks = self._overview_metric(values, "new_active_tasks")
        new_completed_tasks = self._overview_metric(values, "new_completed_tasks")
        my_new_active_tasks = self._overview_metric(values, "my_new_active_tasks")
        my_new_completed_tasks = self._overview_metric(values, "my_new_completed_tasks")

        # Calculate changes
        # Logic: Previous Active = Current Active - New Active + (Total Completed in Period - Completed in Period that were Created in Period)
        # This gives us (Old Active) + (Old Active that became Completed) = Old Active.

        previous_in_progress = (
            in_progress_tasks
            - new_active_tasks
            + (tasks_completed_last_30_days - new_completed_tasks)
        )
        active_tasks_change = self._calculate_percentage_change(
            in_progress_tasks, previous_in_progress
        )

        previous_pending = (
            pending_review_tasks
            - my_new_active_tasks
            + (my_completed_last_30_days - my_new_completed_tasks)
        )
        pending_change = self._calculate_percentage_change(pending_review_tasks, previous_pending)

        velocity_change = self._calculate_percentage_change(team_velocity_val, prev_velocity_val)

        result = {
            "totalProjects": total_projects,
            "totalProjectsChange": self._format_change(projects_change),
            "totalProjectsTrend": "up" if projects_change >= 0 else "down",
            "totalTasks": total_tasks,
            "completedTasks": completed_tasks,
            "inProgressTasks": in_progress_tasks,
            "inProgressTasksChange": self._format_change(active_tasks_change),
            "inProgressTasksTrend": "up" if active_tasks_change >= 0 else "down",
            "pendingReviewTasks": pending_review_tasks,
            "pendingReviewTasksChange": self._format_change(pending_change),
            "pendingReviewTasksTrend": "up" if pending_change >= 0 else "down",
            "teamVelocity": team_velocity_val,
            "teamVelocityChange": self._format_change(velocity_change, _is_percentage_point=True),
            "teamVelocityTrend": "up" if velocity_change >= 0 else "down",
        }

        # B6: Cache result
        await cache_service.set(cache_key, result, ttl=DASHBOARD_CACHE_TTL)
        return result

    async def get_recent_projects(self, user_id: uuid.UUID, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent projects with progress stats using optimized async queries."""
        # B6: Cache recent projects (wrap in dict for cache compatibility)
        cache_key = f"dashboard:recent_projects:{user_id}:{limit}"
        cached = await cache_service.get(cache_key)
        cached_projects = self._get_cached_list(cached)
        if cached_projects is not None:
            return cached_projects

        accessible_projects_subq = self._get_accessible_projects_subquery(user_id)

        # Single query with stats
        query = (
            select(
                Project,
                func.count(Task.id).label("total_tasks"),
                func.sum(
                    case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)
                ).label("completed_tasks"),
            )
            .outerjoin(Task, Task.project_id == Project.id)
            .filter(Project.id.in_(accessible_projects_subq))
            .group_by(Project.id)
            .order_by(desc(Project.updated_at))
            .limit(limit)
        )

        result = await self.db.execute(query)
        projects = self._format_recent_project_rows(result.all())

        # B6: Cache result (wrap list in dict for cache compatibility)
        await cache_service.set(cache_key, {"_list_data": projects}, ttl=DASHBOARD_CACHE_TTL)
        return projects

    async def get_recent_activities(
        self, user_id: uuid.UUID, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get recent team activities using optimized async queries."""
        cache_key = f"dashboard:recent_activities:{user_id}:{limit}"
        cached = await cache_service.get(cache_key)
        cached_activities = self._get_cached_list(cached)
        if cached_activities is not None:
            return cached_activities

        accessible_projects_subq = self._get_accessible_projects_subquery(user_id)

        query = (
            select(TaskHistory, User, Project, Task)
            .join(User, TaskHistory.user_id == User.id)
            .join(Project, TaskHistory.project_id == Project.id)
            .outerjoin(Task, TaskHistory.task_id == Task.id)
            .filter(TaskHistory.project_id.in_(accessible_projects_subq))
            .order_by(desc(TaskHistory.timestamp))
            .limit(limit)
        )

        result = await self.db.execute(query)
        activity_list = self._format_recent_activity_rows(result.all())

        await cache_service.set(cache_key, {"_list_data": activity_list}, ttl=DASHBOARD_CACHE_TTL)
        return activity_list

    async def get_today_tasks(self, user_id: uuid.UUID, limit: int = 10) -> list[dict[str, Any]]:
        """Get tasks assigned to user for today or overdue."""
        # B6: Check cache first (shorter TTL since tasks change more frequently)
        cache_key = f"dashboard:today_tasks:{user_id}:{limit}"
        cached = await cache_service.get(cache_key)
        if isinstance(cached, dict):
            cached_list = cached.get("_list_data")
            if isinstance(cached_list, list):
                cached_tasks: list[dict[str, Any]] = []
                for item in cached_list:
                    if isinstance(item, dict):
                        cached_tasks.append({str(key): value for key, value in item.items()})
                return cached_tasks

        today = date.today()

        query = (
            select(Task)
            .options(selectinload(Task.project))
            .filter(
                Task.assignee_id == user_id, or_(Task.due_date >= today, Task.due_date.is_(None))
            )
            .order_by(Task.due_date.asc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        task_list = [
            {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "status": task.status.value if hasattr(task.status, "value") else str(task.status),
                "priority": task.priority.value if hasattr(task.priority, "value") else "medium",
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "project": {
                    "id": str(task.project.id) if task.project else None,
                    "name": task.project.name if task.project else "Unknown Project",
                },
            }
            for task in tasks
        ]

        # B6: Cache result (shorter TTL for tasks)
        await cache_service.set(cache_key, {"_list_data": task_list}, ttl=60)
        return task_list

    @staticmethod
    def _get_empty_stats_response() -> dict[str, Any]:
        """Return empty stats response for users with no projects."""
        return {
            "totalProjects": 0,
            "totalProjectsChange": "+0%",
            "totalProjectsTrend": "up",
            "totalTasks": 0,
            "completedTasks": 0,
            "inProgressTasks": 0,
            "inProgressTasksChange": "+0%",
            "inProgressTasksTrend": "up",
            "pendingReviewTasks": 0,
            "pendingReviewTasksChange": "+0%",
            "pendingReviewTasksTrend": "up",
            "teamVelocity": 0,
            "teamVelocityChange": "+0%",
            "teamVelocityTrend": "up",
        }

    def _calculate_percentage_change(self, current: float, previous: float) -> float:
        if previous > 0:
            return ((current - previous) / previous) * 100
        return 100 if current > 0 else 0

    def _format_change(self, val: float, _is_percentage_point: bool = False) -> str:
        prefix = "+" if val >= 0 else ""
        suffix = "%"
        return f"{prefix}{round(val, 1)}{suffix}"


async def invalidate_dashboard_cache(user_id: uuid.UUID | None = None) -> None:
    """Invalidate cached dashboard data for one user, or all dashboard entries."""
    if user_id:
        await cache_service.invalidate_pattern(f"dashboard:overview:{user_id}")
        await cache_service.invalidate_pattern(f"dashboard:recent_projects:{user_id}:")
        await cache_service.invalidate_pattern(f"dashboard:recent_activities:{user_id}:")
        await cache_service.invalidate_pattern(f"dashboard:today_tasks:{user_id}:")
        return

    await cache_service.invalidate_pattern("dashboard:")
