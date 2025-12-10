"""
Analytics service for project metrics and productivity data.
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, case, distinct, and_, or_, cast, String, text, extract
from datetime import datetime, timedelta, timezone
import json
import uuid
import threading

from models.project import Project, ProjectMember
from models.task import Task, TaskStatus
from models.task_history import TaskHistory, ActivityType
from models.user import User
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Thread-safe in-memory cache with cleanup
_analytics_cache: Dict[str, Tuple[datetime, Any]] = {}
_cache_lock = threading.RLock()
CACHE_TTL_SECONDS = 300  # 5 minutes
MAX_CACHE_SIZE = 100  # Maximum number of cache entries

def _cleanup_expired_cache():
    """Remove expired entries from cache (called within lock)."""
    now = datetime.now()
    expired_keys = [
        key for key, (timestamp, _) in _analytics_cache.items()
        if (now - timestamp).total_seconds() >= CACHE_TTL_SECONDS
    ]
    for key in expired_keys:
        del _analytics_cache[key]

def _get_from_cache(key: str) -> Optional[Any]:
    """Get value from cache if not expired."""
    with _cache_lock:
        if key in _analytics_cache:
            timestamp, data = _analytics_cache[key]
            if (datetime.now() - timestamp).total_seconds() < CACHE_TTL_SECONDS:
                return data
            # Expired, remove it
            del _analytics_cache[key]
    return None

def _set_cache(key: str, value: Any) -> None:
    """Set value in cache with automatic cleanup if cache is too large."""
    with _cache_lock:
        # Cleanup if cache is getting too large
        if len(_analytics_cache) >= MAX_CACHE_SIZE:
            _cleanup_expired_cache()
            # If still too large, remove oldest entries
            if len(_analytics_cache) >= MAX_CACHE_SIZE:
                oldest_keys = sorted(
                    _analytics_cache.keys(),
                    key=lambda k: _analytics_cache[k][0]
                )[:MAX_CACHE_SIZE // 2]
                for key_to_remove in oldest_keys:
                    del _analytics_cache[key_to_remove]
        _analytics_cache[key] = (datetime.now(), value)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_analytics_overview(self, user_id: uuid.UUID, period: str = "30d") -> Dict[str, Any]:
        """
        Get global analytics overview for the current user across all projects.
        Includes caching for performance (TTL: 5 minutes).
        """
        try:
            # Check cache using thread-safe helper
            cache_key = f"analytics:{user_id}:{period}"
            cached_data = _get_from_cache(cache_key)
            if cached_data is not None:
                logger.info(f"Serving analytics from cache for user {user_id}")
                return cached_data

            # 1. First get all accessible project IDs (Materialize checking)
            # This avoids complex subquery reuse issues in SQLAlchemy
            accessible_projects_query = self.db.query(Project.id).outerjoin(
                ProjectMember, Project.id == ProjectMember.project_id
            ).filter(
                or_(
                    Project.owner_id == user_id,
                    ProjectMember.user_id == user_id
                )
            ).distinct()
            
            project_ids = [p[0] for p in accessible_projects_query.all()]
            
            if not project_ids:
                return self._generate_mock_analytics_data(period)

            # 2. Project stats
            total_projects = len(project_ids)
            
            active_projects = self.db.query(Project.id).filter(
                Project.id.in_(project_ids),
                Project.is_active == True
            ).count()

            # Task stats across all projects
            task_stats = self.db.query(
                func.count(Task.id).label('total'),
                func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed'),
                func.sum(case((cast(Task.status, String) == TaskStatus.IN_PROGRESS.value, 1), else_=0)).label('in_progress'),
                func.sum(case((and_(Task.due_date < datetime.now(), cast(Task.status, String) != TaskStatus.DONE.value), 1), else_=0)).label('overdue')
            ).filter(Task.project_id.in_(project_ids)).first()

            total_tasks = task_stats.total if task_stats else 0
            
            # If valid projects exist but no tasks, return mock data to visualize potential
            if total_tasks == 0:
                 return self._generate_mock_analytics_data(period)

            completed_tasks = task_stats.completed if task_stats and task_stats.completed else 0
            in_progress_tasks = task_stats.in_progress if task_stats and task_stats.in_progress else 0
            overdue_tasks = task_stats.overdue if task_stats and task_stats.overdue else 0

            # Team members (unique users across all accessible projects)
            member_ids_count = self.db.query(func.count(distinct(ProjectMember.user_id))).filter(
                ProjectMember.project_id.in_(project_ids)
            ).scalar() or 0

            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            # Average completion time - DB Optimized
            # Only consider tasks that are completed
            completed_tasks_history = self.db.query(
                TaskHistory.task_id, 
                func.min(TaskHistory.timestamp).label('completed_at')
            ).filter(
                TaskHistory.project_id.in_(project_ids),
                TaskHistory.activity_type == ActivityType.TASK_COMPLETED
            ).group_by(TaskHistory.task_id).subquery()

            avg_seconds = self.db.query(
                func.avg(extract('epoch', completed_tasks_history.c.completed_at) - extract('epoch', Task.created_at))
            ).join(
                completed_tasks_history, Task.id == completed_tasks_history.c.task_id
            ).scalar()
            
            average_completion_time = (avg_seconds / 86400) if avg_seconds else 0

            # Project performance - Aggregated
            project_task_stats = self.db.query(
                Task.project_id,
                func.count(Task.id).label('total'),
                func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed')
            ).filter(
                Task.project_id.in_(project_ids)
            ).group_by(Task.project_id).subquery()
            
            projects_with_stats = self.db.query(
                Project,
                func.coalesce(project_task_stats.c.total, 0),
                func.coalesce(project_task_stats.c.completed, 0)
            ).outerjoin(
                project_task_stats, Project.id == project_task_stats.c.project_id
            ).filter(
                Project.id.in_(project_ids)
            ).all()
            
            projects_data = []
            for p, p_tasks, p_completed in projects_with_stats:
                p_progress = (p_completed / p_tasks * 100) if p_tasks > 0 else 0
                
                velocity = "medium"
                if p_progress > 75:
                    velocity = "high"
                elif p_progress < 25:
                    velocity = "low"
                    
                projects_data.append({
                    "id": str(p.id),
                    "name": p.name,
                    "tasks": p_tasks,
                    "completed": p_completed,
                    "progress": round(p_progress, 1),
                    "velocity": velocity
                })

            # Team performance - Aggregated
            team_stats = self.db.query(
                Task.assignee_id,
                func.count(Task.id).label('total'),
                func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed')
            ).filter(
                Task.project_id.in_(project_ids),
                Task.assignee_id.isnot(None)
            ).group_by(Task.assignee_id).all()
            
            contributor_ids = [stat.assignee_id for stat in team_stats]
            active_users = []
            if contributor_ids:
                active_users = self.db.query(User).filter(User.id.in_(contributor_ids)).all()
            user_map = {u.id: u for u in active_users}
            
            team_data = []
            for stat in team_stats:
                user = user_map.get(stat.assignee_id)
                if not user:
                    continue
                    
                m_tasks = stat.total
                m_completed = stat.completed
                m_efficiency = (m_completed / m_tasks * 100) if m_tasks > 0 else 0
                
                team_data.append({
                    "name": user.name,
                    "avatar": user.avatar_url,
                    "tasks": m_tasks,
                    "completed": m_completed,
                    "efficiency": round(m_efficiency, 1)
                })
            
            team_data.sort(key=lambda x: x['efficiency'], reverse=True)
            team_data = team_data[:5]

            # Determine days based on period
            days_map = {
                "7d": 7, "week": 7, 
                "30d": 30, "month": 30, 
                "90d": 90, "quarter": 90, 
                "1y": 365, "year": 365
            }
            days = days_map.get(period, 30)

            # Burndown Chart
            today = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (today - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            initial_planned = self.db.query(func.count(Task.id)).filter(
                Task.project_id.in_(project_ids),
                Task.created_at < start_date
            ).scalar() or 0
            
            initial_actual = self.db.query(func.count(distinct(TaskHistory.task_id))).filter(
                TaskHistory.project_id.in_(project_ids),
                TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
                TaskHistory.timestamp < start_date
            ).scalar() or 0
            
            created_in_range = self.db.query(Task.created_at).filter(
                Task.project_id.in_(project_ids),
                Task.created_at >= start_date,
                Task.created_at <= today
            ).all()
            
            completed_in_range = self.db.query(TaskHistory.timestamp).filter(
                TaskHistory.project_id.in_(project_ids),
                TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
                TaskHistory.timestamp >= start_date,
                TaskHistory.timestamp <= today
            ).all()
            
            weekly_burndown = []
            created_map = {}
            for (t_created,) in created_in_range:
                if t_created:
                    d_str = t_created.strftime("%Y-%m-%d")
                    created_map[d_str] = created_map.get(d_str, 0) + 1
                    
            completed_map = {}
            for (t_completed,) in completed_in_range:
                if t_completed:
                    d_str = t_completed.strftime("%Y-%m-%d")
                    completed_map[d_str] = completed_map.get(d_str, 0) + 1
                    
            current_planned = initial_planned
            current_actual = initial_actual
            
            # Label format based on duration
            if days <= 7:
                date_fmt = "%a" # Mon, Tue
            elif days <= 60:
                date_fmt = "%d %b" # 01 Jan
            else:
                date_fmt = "%d %b" # 01 Jan (keep it detailed for quarter/year or maybe condense?)

            # Simpler approach: Iterate all days to accumulate, but only add to list based on condition?
            # Or just return all days? 90 days (quarter) is fine. 365 (year) is a bit heavy.
            # Let's stick to returning all days for now to ensure correctness of "current_planned" state.
            
            for i in range(days):
                d = start_date + timedelta(days=i)
                d_str = d.strftime("%Y-%m-%d")
                
                # Determine label
                day_label = d.strftime(date_fmt)
                
                current_planned += created_map.get(d_str, 0)
                current_actual += completed_map.get(d_str, 0)
                
                # For long periods, only add data point every N days to avoid UI clutter
                should_add = True
                if days > 90 and i % 7 != 0 and i != days - 1: # For year, weekly + last day
                     should_add = False
                
                if should_add:
                    weekly_burndown.append({
                        "day": day_label,
                        "planned": current_planned,
                        "actual": current_actual
                    })
            
            # Trends calculation using same 'days'
            current_start = datetime.now() - timedelta(days=days)
            previous_start = current_start - timedelta(days=days)
            
            current_completed_count = self.db.query(func.count(distinct(TaskHistory.task_id))).filter(
                TaskHistory.project_id.in_(project_ids),
                TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
                TaskHistory.timestamp >= current_start
            ).scalar() or 0
            
            previous_completed_count = self.db.query(func.count(distinct(TaskHistory.task_id))).filter(
                TaskHistory.project_id.in_(project_ids),
                TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
                TaskHistory.timestamp >= previous_start,
                TaskHistory.timestamp < current_start
            ).scalar() or 0
            
            completed_change = current_completed_count - previous_completed_count
            div_base = previous_completed_count if previous_completed_count > 0 else 1
            completed_change_pct = (completed_change / div_base * 100)
            
            current_velocity = current_completed_count / days
            previous_velocity = previous_completed_count / days
            velocity_change = current_velocity - previous_velocity
            div_base_vel = previous_velocity if previous_velocity > 0 else 1
            velocity_change_pct = (velocity_change / div_base_vel * 100)
            
            active_members_count = member_ids_count or 1
            current_productivity = current_completed_count / active_members_count
            previous_productivity = previous_completed_count / active_members_count
            productivity_change = current_productivity - previous_productivity
            div_base_prod = previous_productivity if previous_productivity > 0 else 1
            productivity_change_pct = (productivity_change / div_base_prod * 100)
            
            trends = [
                {
                    "metric": "Tasks Completed", 
                    "current": current_completed_count, 
                    "previous": previous_completed_count, 
                    "change": round(completed_change_pct, 1), 
                    "trend": "up" if completed_change >= 0 else "down"
                },
                {
                    "metric": "Project Velocity", 
                    "current": round(current_velocity * 7, 1), # Weekly velocity normalized
                    # Note: velocity is tasks/day * 7. 
                    "previous": round(previous_velocity * 7, 1), 
                    "change": round(velocity_change_pct, 1), 
                    "trend": "up" if velocity_change >= 0 else "down"
                },
                {
                    "metric": "Team Productivity", 
                    "current": round(current_productivity, 1), 
                    "previous": round(previous_productivity, 1), 
                    "change": round(productivity_change_pct, 1), 
                    "trend": "up" if productivity_change >= 0 else "down"
                },
            ]

            # Task Status Distribution
            status_counts = self.db.query(
                cast(Task.status, String).label('status'),
                func.count(Task.id).label('count')
            ).filter(
                Task.project_id.in_(project_ids)
            ).group_by(cast(Task.status, String)).all()
            
            status_distribution = [
                {"name": s.status, "value": s.count} for s in status_counts
            ]

            # Task Priority Breakdown (all tasks, not just active)
            priority_counts = self.db.query(
                cast(Task.priority, String).label('priority'),
                func.count(Task.id).label('count')
            ).filter(
                Task.project_id.in_(project_ids)
            ).group_by(cast(Task.priority, String)).all()
            
            priority_distribution = [
                {"name": p.priority, "value": p.count} for p in priority_counts
            ]

            # Team Workload (All Tasks - not just active)
            workload_counts = self.db.query(
                Task.assignee_id,
                func.count(Task.id).label('count')
            ).filter(
                Task.project_id.in_(project_ids),
                Task.assignee_id.isnot(None)
            ).group_by(Task.assignee_id).all()
            
            workload_data = []
            if workload_counts:
                w_user_ids = [w.assignee_id for w in workload_counts]
                w_users = self.db.query(User).filter(User.id.in_(w_user_ids)).all()
                w_user_map = {u.id: u for u in w_users}
                
                for w in workload_counts:
                    u = w_user_map.get(w.assignee_id)
                    if u:
                        workload_data.append({
                            "name": u.name or u.username,
                            "avatar": u.avatar_url,
                            "tasks": w.count
                        })
                
                # Sort by tasks desc
                workload_data.sort(key=lambda x: x['tasks'], reverse=True)
                workload_data = workload_data[:10] # Top 10

            # Daily Completion vs Creation (using existing maps)
            completion_trends = []
            
            # Using same loop as burndown to generate this chart data
            for i in range(days):
                d = start_date + timedelta(days=i)
                d_str = d.strftime("%Y-%m-%d")
                day_label = d.strftime(date_fmt)
                
                created_count = created_map.get(d_str, 0)
                completed_count = completed_map.get(d_str, 0)
                
                # Similar sampling logic for long periods
                should_add = True
                if days > 90 and i % 7 != 0 and i != days - 1: 
                     should_add = False
                
                if should_add:
                    completion_trends.append({
                        "date": day_label,
                        "created": created_count,
                        "completed": completed_count
                    })

            result = {
                "overview": {
                    "totalProjects": total_projects,
                    "activeProjects": active_projects,
                    "totalTasks": total_tasks,
                    "completedTasks": completed_tasks,
                    "inProgressTasks": in_progress_tasks,
                    "overdueTasks": overdue_tasks,
                    "teamMembers": member_ids_count,
                    "completionRate": round(completion_rate, 1),
                    "averageCompletionTime": round(average_completion_time, 1),
                    "teamVelocity": round(current_velocity * 7, 1), # Weekly velocity
                },
                "trends": trends,
                "projects": projects_data,
                "team": team_data,
                "weeklyBurndown": weekly_burndown,
                "statusDistribution": status_distribution,
                "priorityDistribution": priority_distribution,
                "teamWorkload": workload_data,
                "dailyTrends": completion_trends
            }
            
            # Update cache using thread-safe helper
            _set_cache(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Error generating analytics overview for user {user_id}: {str(e)}")
            # Return empty structure on error to prevent UI crash
            return {
                "overview": {
                    "totalProjects": 0, "activeProjects": 0, "totalTasks": 0, 
                    "completedTasks": 0, "inProgressTasks": 0, "overdueTasks": 0,
                    "teamMembers": 0, "completionRate": 0, "averageCompletionTime": 0, 
                    "teamVelocity": 0
                },
                "trends": [], "projects": [], "team": [], "weeklyBurndown": []
            }

    def _generate_mock_analytics_data(self, period: str) -> Dict[str, Any]:
        """Generate realistic mock data when no real data exists."""
        # Calculate days
        days_map = {
            "7d": 7, "week": 7, 
            "30d": 30, "month": 30, 
            "90d": 90, "quarter": 90, 
            "1y": 365, "year": 365
        }
        days = days_map.get(period, 30)
        
        # Overview
        overview = {
            "totalProjects": 3,
            "activeProjects": 2,
            "totalTasks": 45,
            "completedTasks": 28,
            "inProgressTasks": 12,
            "overdueTasks": 3,
            "teamMembers": 5,
            "completionRate": 62.2,
            "averageCompletionTime": 2.5,
            "teamVelocity": 14.0,
        }
        
        # Trends
        trends = [
            {"metric": "Tasks Completed", "current": 28, "previous": 20, "change": 40.0, "trend": "up"},
            {"metric": "Project Velocity", "current": 14.0, "previous": 12.5, "change": 12.0, "trend": "up"},
            {"metric": "Team Productivity", "current": 5.6, "previous": 4.0, "change": 40.0, "trend": "up"},
        ]
        
        # Projects
        projects = [
            {"id": "mock-1", "name": "Website Redesign", "tasks": 20, "completed": 15, "progress": 75.0, "velocity": "high"},
            {"id": "mock-2", "name": "Mobile App", "tasks": 15, "completed": 5, "progress": 33.3, "velocity": "medium"},
            {"id": "mock-3", "name": "Internal Tools", "tasks": 10, "completed": 8, "progress": 80.0, "velocity": "high"},
        ]
        
        # Team
        team = [
             {"name": "Alice Johnson", "avatar": None, "tasks": 15, "completed": 12, "efficiency": 80.0},
             {"name": "Bob Smith", "avatar": None, "tasks": 12, "completed": 8, "efficiency": 66.7},
             {"name": "Charlie Brown", "avatar": None, "tasks": 10, "completed": 5, "efficiency": 50.0},
             {"name": "Diana Prince", "avatar": None, "tasks": 8, "completed": 3, "efficiency": 37.5},
        ]
        
        # Burndown & Daily Trends
        today = datetime.now()
        start_date = today - timedelta(days=days-1)
        
        weekly_burndown = []
        daily_trends = []
        
        current_planned = 10
        current_actual = 5
        
        date_fmt = "%a" if days <= 7 else "%d %b"
        
        import random
        # No seed for variety or use fixed? Fixed is better for testing.
        random.seed(42) 
        
        for i in range(days):
            d = start_date + timedelta(days=i)
            day_label = d.strftime(date_fmt)
            
            created = random.randint(0, 3)
            completed = random.randint(0, 3)
            
            current_planned += created
            current_actual += completed
            
            should_add = True
            if days > 90 and i % 7 != 0 and i != days - 1: 
                 should_add = False

            if should_add:
                weekly_burndown.append({
                    "day": day_label,
                    "planned": current_planned,
                    "actual": current_actual
                })
                
                daily_trends.append({
                    "date": day_label,
                    "created": created,
                    "completed": completed
                })

        # Status Distribution
        status_distribution = [
            {"name": "Todo", "value": 5},
            {"name": "In Progress", "value": 12},
            {"name": "In Review", "value": 3},
            {"name": "Done", "value": 28},
            {"name": "Cancelled", "value": 1}
        ]
        
        # Priority Distribution
        priority_distribution = [
            {"name": "Urgent", "value": 5},
            {"name": "High", "value": 15},
            {"name": "Medium", "value": 20},
            {"name": "Low", "value": 5}
        ]
        
        # Team Workload
        team_workload = [
            {"name": "Alice Johnson", "avatar": None, "tasks": 8},
            {"name": "Bob Smith", "avatar": None, "tasks": 6},
            {"name": "Charlie Brown", "avatar": None, "tasks": 4},
            {"name": "Diana Prince", "avatar": None, "tasks": 2}
        ]

        return {
            "overview": overview,
            "trends": trends,
            "projects": projects,
            "team": team,
            "weeklyBurndown": weekly_burndown,
            "statusDistribution": status_distribution,
            "priorityDistribution": priority_distribution,
            "teamWorkload": team_workload,
            "dailyTrends": daily_trends
        }

    def get_project_productivity(self, project_id: uuid.UUID, period: str = "30d", group_by: str = "week") -> Dict[str, Any]:
        """Get productivity data for a project."""
        # Calculate date range based on period - use timezone-aware datetimes
        end_date = datetime.now(timezone.utc)
        if period == '7d':
            start_date = end_date - timedelta(days=7)
            days = 7
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
            days = 30
        else:  # 90d
            start_date = end_date - timedelta(days=90)
            days = 90
        
        # Get tasks in date range
        tasks = self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.created_at >= start_date,
            Task.created_at.isnot(None)
        ).all()
        
        # Group by day
        productivity_data = []
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            next_date = current_date + timedelta(days=1)
            
            day_tasks = [t for t in tasks if t.created_at and current_date <= t.created_at < next_date]
            
            created_count = len(day_tasks)
            completed_count = len([t for t in day_tasks if cast(t.status, String) == TaskStatus.DONE.value])
            
            productivity_data.append({
                "date": current_date.isoformat(),
                "created_tasks": created_count,
                "completed_tasks": completed_count
            })
        
        return {
            "period": period,
            "group_by": group_by,
            "data": productivity_data
        }

    def get_project_contributions(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Get team contributions for a project."""
        from sqlalchemy.orm import aliased
        
        # Alias for tasks created by a member
        CreatedTask = aliased(Task)
        # Alias for tasks assigned to and completed by a member
        CompletedTask = aliased(Task)
        # Alias for tasks assigned to a member (total assigned)
        AssignedTask = aliased(Task)

        contributions_query = self.db.query(
            User.id,
            User.name,
            func.count(distinct(CreatedTask.id)).label('tasks_created'),
            func.count(distinct(CompletedTask.id)).label('tasks_completed'),
            func.count(distinct(AssignedTask.id)).label('total_assigned')
        ).join(
            ProjectMember, User.id == ProjectMember.user_id
        ).outerjoin(
            CreatedTask,
            (CreatedTask.project_id == project_id) & (CreatedTask.created_by == User.id)
        ).outerjoin(
            CompletedTask,
            (CompletedTask.project_id == project_id) & (CompletedTask.assignee_id == User.id) & (cast(CompletedTask.status, String) == TaskStatus.DONE.value)
        ).outerjoin(
            AssignedTask,
            (AssignedTask.project_id == project_id) & (AssignedTask.assignee_id == User.id)
        ).filter(
            ProjectMember.project_id == project_id
        ).group_by(
            User.id, User.name
        ).all()
        
        contributions = []
        for user_id, user_name, tasks_created, tasks_completed, total_assigned in contributions_query:
            completion_rate = tasks_completed / max(total_assigned, 1) if total_assigned > 0 else 0.0
            contributions.append({
                "user_id": str(user_id),
                "name": user_name,
                "avatar_url": None, 
                "tasks_created": tasks_created,
                "tasks_completed": tasks_completed,
                "completion_rate": completion_rate
            })
        
        return {
            "project_id": str(project_id),
            "contributions": contributions
        }

    def get_project_dashboard_stats(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Get dashboard metrics for a project."""
        from services.task_history_service import TaskHistoryService
        
        # Check cache
        cache_key = f"project_dashboard:{project_id}"
        cached_data = _get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data

        # Task statistics
        total_tasks = self.db.query(Task).filter(Task.project_id == project_id).count()
        completed_tasks = self.db.query(Task).filter(
            cast(Task.status, String) == TaskStatus.DONE.value
        ).count()
        todo_tasks = self.db.query(Task).filter(
            Task.project_id == project_id,
            cast(Task.status, String) == TaskStatus.TODO.value
        ).count()
        in_progress_tasks = self.db.query(Task).filter(
            Task.project_id == project_id,
            cast(Task.status, String) == TaskStatus.IN_PROGRESS.value
        ).count()
        
        # Member statistics
        from sqlalchemy.orm import joinedload
        members = self.db.query(ProjectMember).options(
            joinedload(ProjectMember.user)
        ).filter(ProjectMember.project_id == project_id).all()
        
        # ... existing activity fetching ...
        
        # Get actual recent activity from database
        task_history_service = TaskHistoryService(self.db)
        
        # Get recent activities from database
        activities = task_history_service.get_recent_activities(project_id, 10)
        
        # Optimize: Get all user IDs from activities
        user_ids = {a.user_id for a in activities}
        users = {}
        if user_ids:
            user_records = self.db.query(User).filter(User.id.in_(user_ids)).all()
            users = {u.id: u for u in user_records}
        
        # Format activities
        recent_activity = []
        for activity in activities:
            # Get user info from map
            user = users.get(activity.user_id)
            user_name = user.name if user else f"User {activity.user_id}"
            
            formatted_activity = {
                "id": str(activity.id),
                "type": activity.activity_type.value,
                "user_name": user_name,
                "task_title": activity.task_title,
                "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,
                "description": activity.description
            }
            
            # Add additional context for specific activity types
            if activity.new_values:
                try:
                    new_values = json.loads(activity.new_values)
                    if "assignee_name" in new_values:
                        formatted_activity["assignee_name"] = new_values["assignee_name"]
                except (json.JSONDecodeError, TypeError):
                    pass
            
            recent_activity.append(formatted_activity)
            
        result = {
            "task_stats": {
                "total": total_tasks,
                "todo": todo_tasks,
                "in_progress": in_progress_tasks,
                "done": completed_tasks
            },
            "member_stats": [
                {
                    "user_id": str(member.user_id),
                    "name": member.user.name if member.user else f"User {member.user_id}",
                    "email": member.user.email if member.user else f"user{member.user_id}@example.com",
                    "avatar_url": member.user.avatar_url if member.user else None
                } for member in members
            ],
            "productivity_score": completed_tasks / max(total_tasks, 1) * 100 if total_tasks > 0 else 0.0,
            "completion_rate": completed_tasks / max(total_tasks, 1) * 100 if total_tasks > 0 else 0.0,
            "recent_activity": recent_activity
        }
        
        _set_cache(cache_key, result)
        return result

    def get_team_workload_paginated(
        self, 
        user_id: uuid.UUID, 
        page: int = 1, 
        page_size: int = 10,
        search: Optional[str] = None,
        sort_by: str = "tasks",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Get paginated team workload data for scalability with large user counts.
        
        Args:
            user_id: Current user ID
            page: Page number (1-indexed)
            page_size: Number of items per page (max 100)
            search: Optional search term for user names
            sort_by: Field to sort by ('tasks' or 'name')
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Paginated team workload data
        """
        try:
            # Validate pagination parameters
            page = max(1, page)
            page_size = min(max(1, page_size), 100)  # Max 100 per page
            
            # Get accessible project IDs
            accessible_projects_query = self.db.query(Project.id).outerjoin(
                ProjectMember, Project.id == ProjectMember.project_id
            ).filter(
                or_(
                    Project.owner_id == user_id,
                    ProjectMember.user_id == user_id
                )
            ).distinct()
            
            project_ids = [p[0] for p in accessible_projects_query.all()]
            
            if not project_ids:
                return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            
            # Build workload query with counts
            workload_query = self.db.query(
                Task.assignee_id,
                func.count(Task.id).label('task_count')
            ).filter(
                Task.project_id.in_(project_ids),
                Task.assignee_id.isnot(None)
            ).group_by(Task.assignee_id)
            
            workload_subquery = workload_query.subquery()
            
            # Join with User table
            user_workload_query = self.db.query(
                User.id,
                User.name,
                User.username,
                User.avatar_url,
                workload_subquery.c.task_count
            ).join(
                workload_subquery, User.id == workload_subquery.c.assignee_id
            )
            
            # Apply search filter
            if search:
                search_pattern = f"%{search}%"
                user_workload_query = user_workload_query.filter(
                    or_(
                        User.name.ilike(search_pattern),
                        User.username.ilike(search_pattern)
                    )
                )
            
            # Get total count before pagination
            total_count = user_workload_query.count()
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
            
            # Apply sorting
            if sort_by == "name":
                order_column = User.name if sort_order == "asc" else User.name.desc()
            else:  # default: tasks
                order_column = workload_subquery.c.task_count.desc() if sort_order == "desc" else workload_subquery.c.task_count
            
            user_workload_query = user_workload_query.order_by(order_column)
            
            # Apply pagination
            offset = (page - 1) * page_size
            results = user_workload_query.offset(offset).limit(page_size).all()
            
            # Format results
            items = []
            for user_id_result, name, username, avatar_url, task_count in results:
                items.append({
                    "name": name or username or f"User {user_id_result}",
                    "avatar": avatar_url,
                    "tasks": task_count
                })
            
            return {
                "items": items,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
            
        except Exception as e:
            logger.error(f"Error getting paginated team workload: {str(e)}")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False
            }
