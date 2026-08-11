"""
Async Analytics service for project metrics and productivity data.
Refactored for SQLAlchemy 2.0+ Async operations.
Uses centralized CacheService for caching.
"""

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import String, and_, case, cast, distinct, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project, ProjectMember
from models.task import Task, TaskStatus
from models.task_history import ActivityType, TaskHistory
from models.user import User
from services.cache_service import cache_service
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Cache TTL in seconds
ANALYTICS_CACHE_TTL = 600  # 10 minutes — analytics data is not real-time critical
ANALYTICS_WORKLOAD_PREVIEW_LIMIT = 10


class AsyncAnalyticsService:
    """Async service class for analytics operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_accessible_projects_subquery(self, user_id: uuid.UUID):
        """Get subquery for projects accessible by the user."""
        return (
            select(Project.id)
            .outerjoin(ProjectMember, Project.id == ProjectMember.project_id)
            .filter(
                Project.is_active.is_(True),
                or_(Project.owner_id == user_id, ProjectMember.user_id == user_id),
            )
            .distinct()
        )

    async def get_analytics_overview(
        self, user_id: uuid.UUID, period: str = "30d"
    ) -> dict[str, Any]:
        """
        Get analytics overview for the current user.
        Optimized for async operations with centralized caching.
        """
        # Check cache using CacheService
        cache_key = f"analytics:overview:{user_id}:{period}"
        cached = await cache_service.get(cache_key)
        if cached:
            logger.debug(f"Serving analytics from cache for user {user_id}")
            return cached

        try:
            # Get accessible project IDs
            accessible_projects_subq = self._get_accessible_projects_subquery(user_id)
            # Get total count efficiently
            count_query = select(func.count()).select_from(accessible_projects_subq.subquery())
            total_projects_result = await self.db.execute(count_query)
            total_projects = total_projects_result.scalar() or 0

            if total_projects == 0:
                result = self._get_empty_analytics_response()
                await cache_service.set(cache_key, result, ttl=ANALYTICS_CACHE_TTL)
                return result

            # Run DB work sequentially on the shared AsyncSession. AsyncSession is not
            # concurrency-safe; cache keeps the warm path fast.
            overview = await self._get_overview_metrics(
                accessible_projects_subq, user_id, total_projects=total_projects
            )
            project_data = await self._get_project_stats(accessible_projects_subq, limit=50)
            team_data = await self._get_team_stats(accessible_projects_subq)

            # Get time-based metrics
            days = self._get_days_from_period(period)

            trends = await self._get_trends(accessible_projects_subq, days)
            distributions = await self._get_distributions(
                accessible_projects_subq,
                workload_limit=ANALYTICS_WORKLOAD_PREVIEW_LIMIT,
            )
            daily_trends = await self._get_daily_trends(accessible_projects_subq, days)

            # Transform daily_trends for weeklyBurndown (Progress)
            weekly_burndown = [
                {"day": d["date"], "planned": d["created"], "actual": d["completed"]}
                for d in daily_trends
            ]

            result = {
                "overview": overview,
                "trends": trends,
                "projects": project_data,  # Already limited by DB
                "team": team_data[:5],  # Top 5
                "statusDistribution": distributions.get("status", []),
                "priorityDistribution": distributions.get("priority", []),
                "teamWorkload": distributions.get("workload", []),
                "teamWorkloadTotal": distributions.get("workloadTotal", 0),
                "weeklyBurndown": weekly_burndown,
                "dailyTrends": daily_trends,
            }

            # Cache result using CacheService
            await cache_service.set(cache_key, result, ttl=ANALYTICS_CACHE_TTL)

            return result

        except Exception as e:
            logger.exception(f"Error generating analytics overview for user {user_id}: {e}")
            raise

    async def _get_overview_metrics(
        self, project_ids: Any, _user_id: uuid.UUID, total_projects: int = 0
    ) -> dict[str, Any]:
        """
        Get overview metrics for the given projects.
        B2: Optimized from 3 queries to 2 by merging active_projects + member_count.
        """
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
                                Task.due_date < datetime.now(UTC),
                                cast(Task.status, String) != TaskStatus.DONE.value,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("overdue_tasks"),
            )
            .filter(Task.project_id.in_(project_ids))
            .cte("analytics_task_stats")
        )
        counts = (
            select(
                func.count(
                    distinct(case((Project.is_active == True, Project.id), else_=None))
                ).label("active_projects"),
                func.count(distinct(ProjectMember.user_id)).label("member_count"),
            )
            .select_from(Project)
            .outerjoin(ProjectMember, Project.id == ProjectMember.project_id)
            .filter(Project.id.in_(project_ids))
            .cte("analytics_project_counts")
        )
        combined_stmt = select(task_stats, counts).select_from(task_stats).join(counts, true())
        combined_result = await self.db.execute(combined_stmt)
        combined_row = combined_result.first()
        values = combined_row._mapping if combined_row is not None else {}

        total_tasks = values["total_tasks"] or 0
        completed_tasks = values["completed_tasks"] or 0
        in_progress_tasks = values["in_progress_tasks"] or 0
        overdue_tasks = values["overdue_tasks"] or 0
        active_projects = values["active_projects"] or 0
        member_count = values["member_count"] or 0

        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        return {
            "totalProjects": total_projects,
            "activeProjects": active_projects,
            "totalTasks": total_tasks,
            "completedTasks": completed_tasks,
            "inProgressTasks": in_progress_tasks,
            "overdueTasks": overdue_tasks,
            "teamMembers": member_count,
            "completionRate": round(completion_rate, 1),
            "averageCompletionTime": 0,  # Can be computed separately if needed
            "teamVelocity": 0,  # Can be computed separately if needed
        }

    async def _get_project_stats(
        self, project_ids: Any, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get stats for each project."""
        # Single query with aggregation
        query = (
            select(
                Project,
                func.count(Task.id).label("task_count"),
                func.sum(
                    case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)
                ).label("completed"),
            )
            .outerjoin(Task, Task.project_id == Project.id)
            .filter(Project.id.in_(project_ids))
            .group_by(Project.id)
            .order_by(Project.name)
        )

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        projects = []
        for project, task_count, completed in rows:
            task_count = task_count or 0
            completed = completed or 0
            progress = round(completed / task_count * 100) if task_count > 0 else 0

            velocity = "medium"
            if progress > 75:
                velocity = "high"
            elif progress < 25:
                velocity = "low"

            projects.append(
                {
                    "id": str(project.id),
                    "name": project.name,
                    "tasks": task_count,
                    "completed": completed,
                    "progress": progress,
                    "velocity": velocity,
                }
            )

        return projects

    async def _get_team_stats(self, project_ids: Any) -> list[dict[str, Any]]:
        """Get team performance stats."""
        query = (
            select(
                User,
                func.count(Task.id).label("total"),
                func.sum(
                    case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)
                ).label("completed"),
            )
            .join(Task, Task.assignee_id == User.id)
            .filter(Task.project_id.in_(project_ids))
            .group_by(User.id)
        )

        result = await self.db.execute(query)
        stats = result.all()

        team_data = []
        for user, total, completed in stats:
            total = total or 0
            completed = completed or 0
            efficiency = round(completed / total * 100) if total > 0 else 0

            team_data.append(
                {
                    "name": user.name,
                    "avatar": user.avatar_url,
                    "tasks": total,
                    "completed": completed,
                    "efficiency": efficiency,
                }
            )

        team_data.sort(key=lambda x: float(x.get("efficiency", 0) or 0), reverse=True)
        return team_data

    async def _get_trends(self, project_ids: Any, days: int) -> list[dict[str, Any]]:
        """Get performance trends."""
        current_start = datetime.now(UTC) - timedelta(days=days)
        previous_start = current_start - timedelta(days=days)

        trend_result = await self.db.execute(
            select(
                func.count(
                    distinct(
                        case(
                            (
                                TaskHistory.timestamp >= current_start,
                                TaskHistory.task_id,
                            )
                        )
                    )
                ).label("current_completed"),
                func.count(
                    distinct(
                        case(
                            (
                                and_(
                                    TaskHistory.timestamp >= previous_start,
                                    TaskHistory.timestamp < current_start,
                                ),
                                TaskHistory.task_id,
                            )
                        )
                    )
                ).label("previous_completed"),
            ).filter(
                TaskHistory.project_id.in_(project_ids),
                cast(TaskHistory.activity_type, String) == ActivityType.TASK_COMPLETED.value,
                TaskHistory.timestamp >= previous_start,
            )
        )
        trend_values = trend_result.first()
        current_completed = trend_values.current_completed if trend_values is not None else 0
        previous_completed = trend_values.previous_completed if trend_values is not None else 0

        # Calculate changes
        completed_change = self._calculate_percentage_change(current_completed, previous_completed)

        current_velocity = current_completed / days if days > 0 else 0
        previous_velocity = previous_completed / days if days > 0 else 0
        velocity_change = self._calculate_percentage_change(current_velocity, previous_velocity)

        return [
            {
                "metric": "Tasks Completed",
                "current": current_completed,
                "previous": previous_completed,
                "change": round(completed_change, 1),
                "trend": "up" if completed_change >= 0 else "down",
            },
            {
                "metric": "Project Velocity",
                "current": round(current_velocity * 7, 1),
                "previous": round(previous_velocity * 7, 1),
                "change": round(velocity_change, 1),
                "trend": "up" if velocity_change >= 0 else "down",
            },
        ]

    async def _get_daily_trends(self, project_ids: Any, days: int) -> list[dict[str, Any]]:
        """Get daily trends for task creation and completion."""
        # Calculate start date
        start_date = datetime.now(UTC) - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.date(TaskHistory.timestamp).label("date"),
                cast(TaskHistory.activity_type, String).label("activity_type"),
                func.count(TaskHistory.id).label("count"),
            )
            .filter(
                TaskHistory.project_id.in_(project_ids),
                cast(TaskHistory.activity_type, String).in_(
                    [ActivityType.TASK_CREATED.value, ActivityType.TASK_COMPLETED.value]
                ),
                TaskHistory.timestamp >= start_date,
            )
            .group_by(
                func.date(TaskHistory.timestamp),
                cast(TaskHistory.activity_type, String),
            )
        )
        created_counts: dict[str, int] = {}
        completed_counts: dict[str, int] = {}
        for row in result.all():
            row_mapping = getattr(row, "_mapping", None)
            raw_count: Any = (
                row_mapping.get("count")
                if isinstance(row_mapping, Mapping)
                else getattr(row, "count", 0)
            )
            if row.activity_type == ActivityType.TASK_CREATED.value:
                created_counts[str(row.date)] = int(raw_count)
            else:
                completed_counts[str(row.date)] = int(raw_count)

        # Generate complete date range (analytics charts expect continuous dates)
        trends = []
        for i in range(days):
            date = (datetime.now(UTC) - timedelta(days=days - i - 1)).date()
            date_str = str(date)
            # Find matching format from DB (could be YYYY-MM-DD)

            created = 0
            completed = 0

            # Simple matching for YYYY-MM-DD
            if date_str in created_counts:
                created = created_counts[date_str]
            if date_str in completed_counts:
                completed = completed_counts[date_str]

            trends.append(
                {
                    "date": date.strftime("%b %d"),  # Format for frontend display
                    "fullDate": date_str,
                    "created": created,
                    "completed": completed,
                }
            )

        return trends

    async def _get_distributions(
        self, project_ids: Any, workload_limit: int | None = None
    ) -> dict[str, Any]:
        """Get status, priority, and workload distributions."""
        # Status distribution
        status_result = await self.db.execute(
            select(cast(Task.status, String).label("status"), func.count(Task.id).label("count"))
            .filter(Task.project_id.in_(project_ids))
            .group_by(cast(Task.status, String))
        )
        status_counts = status_result.all()
        status_dist = [{"name": s[0], "value": s[1]} for s in status_counts]

        # Priority distribution
        priority_result = await self.db.execute(
            select(
                cast(Task.priority, String).label("priority"), func.count(Task.id).label("count")
            )
            .filter(Task.project_id.in_(project_ids))
            .group_by(cast(Task.priority, String))
        )
        priority_counts = priority_result.all()
        priority_dist = [{"name": p[0], "value": p[1]} for p in priority_counts]

        # Workload distribution
        workload_total_result = await self.db.execute(
            select(func.count(distinct(Task.assignee_id))).filter(
                Task.project_id.in_(project_ids), Task.assignee_id.isnot(None)
            )
        )
        workload_total = workload_total_result.scalar() or 0

        workload_query = (
            select(User, func.count(Task.id).label("count"))
            .join(Task, Task.assignee_id == User.id)
            .filter(Task.project_id.in_(project_ids))
            .group_by(User.id)
            .order_by(
                func.count(Task.id).desc(), func.coalesce(User.name, User.username, User.email)
            )
        )
        if workload_limit is not None:
            workload_query = workload_query.limit(workload_limit)
        workload_result = await self.db.execute(workload_query)
        workload_rows = workload_result.all()

        workload_dist = []
        for user, count in workload_rows:
            workload_dist.append(
                {
                    "name": user.name or user.username,
                    "avatar": user.avatar_url,
                    "tasks": count,
                }
            )

        return {
            "status": status_dist,
            "priority": priority_dist,
            "workload": workload_dist,
            "workloadTotal": workload_total,
        }

    async def get_project_analytics(self, project_id: uuid.UUID) -> dict[str, Any]:
        """Get analytics for a specific project."""
        # Task stats
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
                    case((cast(Task.status, String) == TaskStatus.TODO.value, 1), else_=0)
                ).label("todo"),
            ).filter(Task.project_id == project_id)
        )
        stats = task_stats_result.first()

        total = stats[0] or 0
        completed = stats[1] or 0
        in_progress = stats[2] or 0
        todo = stats[3] or 0

        # Member stats
        member_result = await self.db.execute(
            select(func.count(ProjectMember.id)).filter(ProjectMember.project_id == project_id)
        )
        member_count = member_result.scalar() or 0

        completion_rate = round(completed / total * 100) if total > 0 else 0

        return {
            "task_stats": {
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "todo": todo,
            },
            "member_count": member_count,
            "completion_rate": completion_rate,
            "productivity_score": completion_rate,
        }

    def _get_days_from_period(self, period: str) -> int:
        """Convert period string to days."""
        days_map = {
            "7d": 7,
            "week": 7,
            "30d": 30,
            "month": 30,
            "90d": 90,
            "quarter": 90,
            "1y": 365,
            "year": 365,
        }
        return days_map.get(period, 30)

    def _calculate_percentage_change(self, current: float, previous: float) -> float:
        """Calculate percentage change."""
        if previous > 0:
            return ((current - previous) / previous) * 100
        return 100 if current > 0 else 0

    def _get_empty_analytics_response(self) -> dict[str, Any]:
        """Return empty analytics response."""
        return {
            "overview": {
                "totalProjects": 0,
                "activeProjects": 0,
                "totalTasks": 0,
                "completedTasks": 0,
                "inProgressTasks": 0,
                "overdueTasks": 0,
                "teamMembers": 0,
                "completionRate": 0,
                "averageCompletionTime": 0,
                "teamVelocity": 0,
            },
            "trends": [],
            "projects": [],
            "team": [],
            "weeklyBurndown": [],
            "statusDistribution": [],
            "priorityDistribution": [],
            "teamWorkload": [],
            "teamWorkloadTotal": 0,
            "dailyTrends": [],
        }

    @staticmethod
    def _order_workload_query(
        query: Any, sort_by: str, sort_order: str, sort_by_name: Any, task_count: Any
    ) -> Any:
        if sort_by == "name":
            if sort_order == "asc":
                return query.order_by(sort_by_name.asc(), task_count.desc())
            return query.order_by(sort_by_name.desc(), task_count.desc())
        if sort_order == "asc":
            return query.order_by(task_count.asc(), sort_by_name.asc())
        return query.order_by(task_count.desc(), sort_by_name.asc())

    # Extend AsyncAnalyticsService with additional methods
    async def get_team_workload_paginated(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        sort_by: str = "tasks",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """
        Get paginated team workload data for scalability.
        """
        accessible_projects_subq = self._get_accessible_projects_subquery(user_id)
        completed_count = func.sum(
            case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)
        ).label("completed_count")
        task_count = func.count(Task.id).label("task_count")
        user_name = func.coalesce(User.name, User.username, User.email)

        query = (
            select(
                User.id.label("user_id"),
                user_name.label("user_name"),
                User.avatar_url.label("avatar_url"),
                task_count,
                completed_count,
            )
            .join(User, User.id == Task.assignee_id)
            .filter(Task.project_id.in_(accessible_projects_subq), Task.assignee_id.isnot(None))
            .group_by(User.id)
        )

        if search:
            query = query.filter(
                func.lower(func.coalesce(User.name, User.username, User.email)).contains(
                    search.lower()
                )
            )

        sort_by_name = func.coalesce(User.name, User.username, User.email)
        query = self._order_workload_query(query, sort_by, sort_order, sort_by_name, task_count)

        count_result = await self.db.execute(
            select(func.count()).select_from(query.order_by(None).subquery())
        )
        total_count = count_result.scalar() or 0

        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size
        result = await self.db.execute(query.offset(offset).limit(page_size))
        stats = result.all()
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
        has_next = page < total_pages
        has_prev = page > 1 and total_count > 0

        if not stats:
            return {
                "items": [],
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": False,
                "has_prev": has_prev,
            }

        items = []
        for (
            assignee_id,
            assignee_name,
            avatar_url,
            member_task_count,
            member_completed_count,
        ) in stats:
            items.append(
                {
                    "id": str(assignee_id),
                    "name": assignee_name,
                    "avatar": avatar_url,
                    "tasks": member_task_count or 0,
                    "completed": member_completed_count or 0,
                    "progress": round(
                        (member_completed_count or 0) / (member_task_count or 1) * 100
                    ),
                }
            )

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
        }

    async def get_project_productivity(
        self, project_id: uuid.UUID, period: str = "30d", group_by: str = "week"
    ) -> dict[str, Any]:
        """
        Get productivity data for a project.
        """
        days = self._get_days_from_period(period)
        start_date = datetime.now(UTC) - timedelta(days=days)

        group_by = group_by.lower()
        if group_by == "day":
            group_expression = func.date(TaskHistory.timestamp)
        elif group_by == "month":
            group_expression = func.date_trunc("month", TaskHistory.timestamp)
        else:
            group_by = "week"
            group_expression = func.date_trunc("week", TaskHistory.timestamp)

        # Get task completions over time
        completions_result = await self.db.execute(
            select(
                group_expression.label("date"),
                func.count(TaskHistory.id).label("count"),
            )
            .filter(
                TaskHistory.project_id == project_id,
                cast(TaskHistory.activity_type, String) == ActivityType.TASK_COMPLETED.value,
                TaskHistory.timestamp >= start_date,
            )
            .group_by(group_expression)
            .order_by(group_expression)
        )
        completions = completions_result.all()

        # Format data points
        data_points = []
        for date_val, count in completions:
            data_points.append({"date": str(date_val) if date_val else None, "completed": count})

        return {
            "period": period,
            "groupBy": group_by,
            "data": data_points,
            "totalCompleted": sum(d["completed"] for d in data_points),
        }

    async def get_project_contributions(self, project_id: uuid.UUID) -> dict[str, Any]:
        """
        Get team contributions for a project.
        """
        query = (
            select(
                Task.assignee_id,
                func.count(Task.id).label("total"),
                func.sum(
                    case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)
                ).label("completed"),
            )
            .filter(Task.project_id == project_id, Task.assignee_id.isnot(None))
            .group_by(Task.assignee_id)
        )

        result = await self.db.execute(query)
        stats = result.all()

        if not stats:
            return {"contributors": [], "totalTasks": 0, "totalCompleted": 0}

        # Get user info
        user_ids = [s[0] for s in stats]
        users_result = await self.db.execute(select(User).filter(User.id.in_(user_ids)))
        users = {u.id: u for u in users_result.scalars().all()}

        contributors = []
        total_tasks = 0
        total_completed = 0

        for assignee_id, task_total, completed in stats:
            user = users.get(assignee_id)
            if not user:
                continue

            task_total = task_total or 0
            completed = completed or 0
            total_tasks += task_total
            total_completed += completed

            contributors.append(
                {
                    "id": str(user.id),
                    "name": user.name,
                    "avatar": user.avatar_url,
                    "tasks": task_total,
                    "completed": completed,
                    "percentage": 0,  # Will be calculated after total is known
                }
            )

        # Calculate percentages
        for contributor in contributors:
            if total_tasks > 0:
                contributor["percentage"] = round(
                    float(contributor.get("tasks", 0) or 0) / total_tasks * 100
                )

        contributors.sort(key=lambda x: int(x.get("tasks", 0) or 0), reverse=True)

        return {
            "contributors": contributors,
            "totalTasks": total_tasks,
            "totalCompleted": total_completed,
        }


async def invalidate_analytics_cache(user_id: uuid.UUID | None = None):
    """Invalidate analytics cache for a user or all users using CacheService."""
    if user_id:
        # Invalidate user-specific analytics cache
        await cache_service.invalidate_pattern(f"analytics:overview:{user_id}")
    else:
        # Clear all analytics cache
        await cache_service.invalidate_pattern("analytics:")
