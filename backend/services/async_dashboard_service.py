"""
Async Dashboard service for analytics and statistics.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import String, and_, case, cast, desc, distinct, func, or_, select
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
            .filter(or_(Project.owner_id == user_id, ProjectMember.user_id == user_id))
        )

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

        project_stats_result = await self.db.execute(
            select(
                func.count(distinct(Project.id)).label("total"),
                func.count(
                    distinct(case((Project.created_at >= thirty_days_ago, Project.id)))
                ).label("created_30d"),
            ).filter(Project.id.in_(accessible_projects_subq))
        )
        project_stats = project_stats_result.first()

        if not project_stats or not project_stats.total:
            return self._get_empty_stats_response()

        task_stats_result = await self.db.execute(
            select(
                func.count(Task.id).label("total"),
                func.sum(
                    case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)
                ).label("completed"),
                func.sum(
                    case((cast(Task.status, String) == TaskStatus.IN_PROGRESS.value, 1), else_=0)
                ).label("in_progress"),
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
                ).label("pending_review"),
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
                ).label("new_active"),
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
                ).label("new_completed"),
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
                ).label("my_new_active"),
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
                ).label("my_new_completed"),
            ).filter(Task.project_id.in_(accessible_projects_subq))
        )
        task_stats = task_stats_result.first()

        history_stats_result = await self.db.execute(
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
            ).filter(
                TaskHistory.project_id.in_(accessible_projects_subq),
                TaskHistory.timestamp >= thirty_days_ago,
            )
        )
        history_stats = history_stats_result.first()

        total_projects = project_stats.total if project_stats and project_stats.total else 0
        projects_created_last_30_days = (
            project_stats.created_30d if project_stats and project_stats.created_30d else 0
        )

        # Process Results
        if total_projects == 0:
            return self._get_empty_stats_response()

        total_tasks = task_stats.total if task_stats else 0
        completed_tasks = task_stats.completed if task_stats and task_stats.completed else 0
        in_progress_tasks = task_stats.in_progress if task_stats and task_stats.in_progress else 0
        pending_review_tasks = (
            task_stats.pending_review if task_stats and task_stats.pending_review else 0
        )

        # Trends processing
        previous_total_projects = total_projects - projects_created_last_30_days
        projects_change = self._calculate_percentage_change(total_projects, previous_total_projects)

        tasks_completed_last_30_days = (
            history_stats.completed_30d if history_stats and history_stats.completed_30d else 0
        )
        my_completed_last_30_days = (
            history_stats.my_completed_30d
            if history_stats and history_stats.my_completed_30d
            else 0
        )
        team_velocity_val = (
            history_stats.velocity_7d if history_stats and history_stats.velocity_7d else 0
        )
        prev_velocity_val = (
            history_stats.velocity_prev_7d
            if history_stats and history_stats.velocity_prev_7d
            else 0
        )

        new_active_tasks = task_stats.new_active if task_stats and task_stats.new_active else 0
        new_completed_tasks = (
            task_stats.new_completed if task_stats and task_stats.new_completed else 0
        )

        my_new_active_tasks = (
            task_stats.my_new_active if task_stats and task_stats.my_new_active else 0
        )
        my_new_completed_tasks = (
            task_stats.my_new_completed if task_stats and task_stats.my_new_completed else 0
        )

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
        await cache_service.set(cache_key, result, timeout=DASHBOARD_CACHE_TTL)
        return result

    async def get_recent_projects(self, user_id: uuid.UUID, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent projects with progress stats using optimized async queries."""
        # B6: Cache recent projects (wrap in dict for cache compatibility)
        cache_key = f"dashboard:recent_projects:{user_id}:{limit}"
        cached = await cache_service.get(cache_key)
        if isinstance(cached, dict):
            cached_list = cached.get("_list_data")
            if isinstance(cached_list, list):
                cached_projects: list[dict[str, Any]] = []
                for item in cached_list:
                    if isinstance(item, dict):
                        cached_projects.append({str(key): value for key, value in item.items()})
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
        rows = result.all()

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
                    "color": "#6366f1",
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                }
            )

        # B6: Cache result (wrap list in dict for cache compatibility)
        await cache_service.set(cache_key, {"_list_data": projects}, timeout=DASHBOARD_CACHE_TTL)
        return projects

    async def get_recent_activities(
        self, user_id: uuid.UUID, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get recent team activities using optimized async queries."""
        cache_key = f"dashboard:recent_activities:{user_id}:{limit}"
        cached = await cache_service.get(cache_key)
        if isinstance(cached, dict):
            cached_list = cached.get("_list_data")
            if isinstance(cached_list, list):
                cached_activities: list[dict[str, Any]] = []
                for item in cached_list:
                    if isinstance(item, dict):
                        cached_activities.append({str(key): value for key, value in item.items()})
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
        rows = result.all()

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

        activity_list = []
        for activity, user, project, task in rows:
            activity_type_str = (
                activity.activity_type.value
                if hasattr(activity.activity_type, "value")
                else str(activity.activity_type)
            )
            action = action_map.get(activity_type_str, "performed action")

            activity_list.append(
                {
                    "id": str(activity.id),
                    "user": {
                        "name": user.name if user else "Unknown User",
                        "id": str(activity.user_id),
                        "avatar": user.avatar_url if user else None,
                    },
                    "action": action,
                    "target": task.title
                    if task
                    else (project.name if project else "Unknown Target"),
                    "time": activity.timestamp.isoformat() if activity.timestamp else None,
                    "project": {
                        "name": project.name if project else "Unknown Project",
                        "id": str(activity.project_id) if project else None,
                    }
                    if project
                    else None,
                }
            )

        await cache_service.set(
            cache_key, {"_list_data": activity_list}, timeout=DASHBOARD_CACHE_TTL
        )
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
        await cache_service.set(cache_key, {"_list_data": task_list}, timeout=60)
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
