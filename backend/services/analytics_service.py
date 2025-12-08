"""
Analytics service for project metrics and productivity data.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, case, distinct, and_, or_, cast, String, text, extract
from datetime import datetime, timedelta, timezone
import json
import uuid

from models.project import Project, ProjectMember
from models.task import Task, TaskStatus
from models.task_history import TaskHistory, ActivityType
from models.user import User
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Simple in-memory cache
_analytics_cache: Dict[str, Any] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_analytics_overview(self, user_id: uuid.UUID, period: str = "30d") -> Dict[str, Any]:
        """
        Get global analytics overview for the current user across all projects.
        Includes caching for performance (TTL: 5 minutes).
        """
        # Check cache
        cache_key = f"{user_id}:{period}"
        now = datetime.now()
        
        if cache_key in _analytics_cache:
            cached_ts, cached_data = _analytics_cache[cache_key]
            if (now - cached_ts).total_seconds() < CACHE_TTL_SECONDS:
                logger.info(f"Serving analytics from cache for user {user_id}")
                return cached_data

        # Efficient Subquery for accessible projects
        accessible_projects_subquery = self.db.query(Project.id).outerjoin(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(
            or_(
                Project.owner_id == user_id,
                ProjectMember.user_id == user_id
            )
        )

        # 1. Project stats
        total_projects = self.db.query(func.count(distinct(Project.id))).outerjoin(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(
            or_(
                Project.owner_id == user_id,
                ProjectMember.user_id == user_id
            )
        ).scalar() or 0
        
        if total_projects == 0:
            result = {
                "overview": {
                    "totalProjects": 0, "activeProjects": 0,
                    "totalTasks": 0, "completedTasks": 0, "inProgressTasks": 0, "overdueTasks": 0,
                    "teamMembers": 0, "completionRate": 0, "averageCompletionTime": 0, "teamVelocity": 0,
                },
                "trends": [], "projects": [], "team": [], "weeklyBurndown": []
            }
            return result

        active_projects = self.db.query(func.count(distinct(Project.id))).outerjoin(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(
            or_(
                Project.owner_id == user_id,
                ProjectMember.user_id == user_id
            ),
            Project.is_active == True
        ).scalar() or 0

        # Task stats across all projects
        task_stats = self.db.query(
            func.count(Task.id).label('total'),
            func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed'),
            func.sum(case((cast(Task.status, String) == TaskStatus.IN_PROGRESS.value, 1), else_=0)).label('in_progress'),
            func.sum(case((and_(Task.due_date < datetime.now(), cast(Task.status, String) != TaskStatus.DONE.value), 1), else_=0)).label('overdue')
        ).filter(Task.project_id.in_(accessible_projects_subquery)).first()

        total_tasks = task_stats.total if task_stats else 0
        completed_tasks = task_stats.completed if task_stats and task_stats.completed else 0
        in_progress_tasks = task_stats.in_progress if task_stats and task_stats.in_progress else 0
        overdue_tasks = task_stats.overdue if task_stats and task_stats.overdue else 0

        # Team members (unique users across all accessible projects)
        member_ids_count = self.db.query(func.count(distinct(ProjectMember.user_id))).filter(
            ProjectMember.project_id.in_(accessible_projects_subquery)
        ).scalar() or 0

        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Average completion time - DB Optimized
        min_completion_dates = self.db.query(
            TaskHistory.task_id, 
            func.min(TaskHistory.timestamp).label('completed_at')
        ).filter(
            TaskHistory.project_id.in_(accessible_projects_subquery),
            TaskHistory.activity_type == ActivityType.TASK_COMPLETED
        ).group_by(TaskHistory.task_id).subquery()

        avg_seconds = self.db.query(
            func.avg(extract('epoch', min_completion_dates.c.completed_at) - extract('epoch', Task.created_at))
        ).join(
            min_completion_dates, Task.id == min_completion_dates.c.task_id
        ).scalar()
        
        average_completion_time = (avg_seconds / 86400) if avg_seconds else 0

        # Project performance - Aggregated
        project_task_stats = self.db.query(
            Task.project_id,
            func.count(Task.id).label('total'),
            func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed')
        ).filter(
            Task.project_id.in_(accessible_projects_subquery)
        ).group_by(Task.project_id).subquery()
        
        projects_with_stats = self.db.query(
            Project,
            func.coalesce(project_task_stats.c.total, 0),
            func.coalesce(project_task_stats.c.completed, 0)
        ).outerjoin(
            project_task_stats, Project.id == project_task_stats.c.project_id
        ).filter(
            Project.id.in_(accessible_projects_subquery)
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
            Task.project_id.in_(accessible_projects_subquery),
            Task.assignee_id.isnot(None)
        ).group_by(Task.assignee_id).all()
        
        contributor_ids = [stat.assignee_id for stat in team_stats]
        users = self.db.query(User).filter(User.id.in_(contributor_ids)).all()
        user_map = {u.id: u for u in users}
        
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

        # Weekly Burndown
        today = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        seven_days_ago = (today - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        initial_planned = self.db.query(func.count(Task.id)).filter(
            Task.project_id.in_(accessible_projects_subquery),
            Task.created_at < seven_days_ago
        ).scalar() or 0
        
        initial_actual = self.db.query(func.count(distinct(TaskHistory.task_id))).filter(
            TaskHistory.project_id.in_(accessible_projects_subquery),
            TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
            TaskHistory.timestamp < seven_days_ago
        ).scalar() or 0
        
        created_in_range = self.db.query(Task.created_at).filter(
            Task.project_id.in_(accessible_projects_subquery),
            Task.created_at >= seven_days_ago,
            Task.created_at <= today
        ).all()
        
        completed_in_range = self.db.query(TaskHistory.timestamp).filter(
            TaskHistory.project_id.in_(accessible_projects_subquery),
            TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
            TaskHistory.timestamp >= seven_days_ago,
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
        
        for i in range(7):
            d = seven_days_ago + timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            day_label = d.strftime("%a")
            
            current_planned += created_map.get(d_str, 0)
            current_actual += completed_map.get(d_str, 0)
            
            weekly_burndown.append({
                "day": day_label,
                "planned": current_planned,
                "actual": current_actual
            })
        
        # Trends
        days_map = {
            "7d": 7, "week": 7, 
            "30d": 30, "month": 30, 
            "90d": 90, "quarter": 90, 
            "1y": 365, "year": 365
        }
        days = days_map.get(period, 30)
        
        current_start = datetime.now() - timedelta(days=days)
        previous_start = current_start - timedelta(days=days)
        
        current_completed_count = self.db.query(func.count(distinct(TaskHistory.task_id))).filter(
            TaskHistory.project_id.in_(accessible_projects_subquery),
            TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
            TaskHistory.timestamp >= current_start
        ).scalar() or 0
        
        previous_completed_count = self.db.query(func.count(distinct(TaskHistory.task_id))).filter(
            TaskHistory.project_id.in_(accessible_projects_subquery),
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
                "current": round(current_velocity * 7, 1), # Weekly velocity
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
            "weeklyBurndown": weekly_burndown
        }
        
        # Update cache
        _analytics_cache[cache_key] = (now, result)
        
        return result

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
        members = self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
        
        # Get actual recent activity from database
        task_history_service = TaskHistoryService(self.db)
        
        # Get recent activities from database
        activities = task_history_service.get_recent_activities(project_id, 10)
        
        # Format activities
        recent_activity = []
        for activity in activities:
            # Get user info
            user = self.db.query(User).filter(User.id == activity.user_id).first()
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
            
        return {
            "task_stats": {
                "total": total_tasks,
                "todo": todo_tasks,
                "in_progress": in_progress_tasks,
                "done": completed_tasks
            },
            "member_stats": [
                {
                    "user_id": str(member.user_id),
                    "name": f"User {member.user_id}",
                    "email": f"user{member.user_id}@example.com"
                } for member in members
            ],
            "productivity_score": completed_tasks / max(total_tasks, 1) * 100 if total_tasks > 0 else 0.0,
            "completion_rate": completed_tasks / max(total_tasks, 1) * 100 if total_tasks > 0 else 0.0,
            "recent_activity": recent_activity
        }
