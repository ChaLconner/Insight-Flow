"""
Dashboard service for analytics and statistics.
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, cast, String, case, and_, or_, distinct
from models.user import User
from models.project import Project, ProjectMember
from models.task import Task, TaskStatus
from models.task_history import TaskHistory, ActivityType
from utils.cache import cache_dashboard_stats
import uuid

class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def _get_accessible_projects_query(self, user_id: uuid.UUID):
        """
        Get subquery for projects accessible by the user (owned or member).
        """
        return self.db.query(Project.id).outerjoin(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(
            or_(
                Project.owner_id == user_id,
                ProjectMember.user_id == user_id
            )
        )

    @cache_dashboard_stats(ttl_seconds=60)  # Cache stats for 60 seconds
    def get_overview_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get dashboard overview statistics.
        Results are cached for 60 seconds per user.
        """
        accessible_projects_subquery = self._get_accessible_projects_query(user_id)


        # 1. Total Projects
        total_projects = self.db.query(func.count(distinct(Project.id))).outerjoin(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(
            or_(
                Project.owner_id == user_id,
                ProjectMember.user_id == user_id
            )
        ).scalar() or 0
        
        if total_projects == 0:
            return {
                "totalProjects": 0, "totalProjectsChange": "+0%", "totalProjectsTrend": "up",
                "totalTasks": 0, "completedTasks": 0,
                "inProgressTasks": 0, "inProgressTasksChange": "+0%", "inProgressTasksTrend": "up",
                "pendingReviewTasks": 0, "pendingReviewTasksChange": "+0%", "pendingReviewTasksTrend": "up",
                "teamVelocity": 0, "teamVelocityChange": "+0%", "teamVelocityTrend": "up"
            }

        # Aggregate task statistics
        task_stats = self.db.query(
            func.count(Task.id).label('total'),
            func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed'),
            func.sum(case((cast(Task.status, String) == TaskStatus.IN_PROGRESS.value, 1), else_=0)).label('in_progress'),
            func.sum(case((and_(
                Task.assignee_id == user_id, 
                cast(Task.status, String) == TaskStatus.IN_PROGRESS.value
            ), 1), else_=0)).label('pending_review')
        ).filter(
            Task.project_id.in_(accessible_projects_subquery)
        ).first()
        
        total_tasks = task_stats.total if task_stats else 0
        completed_tasks = task_stats.completed if task_stats and task_stats.completed else 0
        in_progress_tasks = task_stats.in_progress if task_stats and task_stats.in_progress else 0
        pending_review_tasks = task_stats.pending_review if task_stats and task_stats.pending_review else 0
        
        # Calculate team velocity (percentage of completed tasks)
        # Note: Previous logic was (completed / total * 100), technically this is "Completion Rate", not Velocity. 
        # But keeping consistent with existing logic.
        team_velocity = round((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
        
        # Calculate trends
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
        
        # Total Projects Change
        projects_created_last_30_days = self.db.query(Project).filter(
            Project.id.in_(accessible_projects_subquery),
            Project.created_at >= thirty_days_ago
        ).count()
        
        previous_total_projects = total_projects - projects_created_last_30_days
        projects_change = self._calculate_percentage_change(total_projects, previous_total_projects)
            
        # History Metrics for trends
        history_stats = self.db.query(
            func.sum(case((and_(TaskHistory.activity_type == ActivityType.TASK_COMPLETED, TaskHistory.timestamp >= thirty_days_ago), 1), else_=0)).label('completed_30d'),
            func.sum(case((and_(TaskHistory.user_id == user_id, TaskHistory.activity_type == ActivityType.TASK_COMPLETED, TaskHistory.timestamp >= thirty_days_ago), 1), else_=0)).label('my_completed_30d'),
            func.sum(case((and_(TaskHistory.activity_type == ActivityType.TASK_COMPLETED, TaskHistory.timestamp >= seven_days_ago), 1), else_=0)).label('velocity_7d'),
            func.sum(case((and_(TaskHistory.activity_type == ActivityType.TASK_COMPLETED, TaskHistory.timestamp >= fourteen_days_ago, TaskHistory.timestamp < seven_days_ago), 1), else_=0)).label('velocity_prev_7d')
        ).filter(
            TaskHistory.project_id.in_(accessible_projects_subquery),
            TaskHistory.timestamp >= thirty_days_ago
        ).first()
        
        tasks_completed_last_30_days = history_stats.completed_30d if history_stats and history_stats.completed_30d else 0
        my_completed_last_30_days = history_stats.my_completed_30d if history_stats and history_stats.my_completed_30d else 0
        team_velocity_val = history_stats.velocity_7d if history_stats and history_stats.velocity_7d else 0
        prev_velocity_val = history_stats.velocity_prev_7d if history_stats and history_stats.velocity_prev_7d else 0

        # Task Creation Metrics
        task_creation_stats = self.db.query(
            func.sum(case((cast(Task.status, String) == TaskStatus.IN_PROGRESS.value, 1), else_=0)).label('new_active'),
            func.sum(case((and_(Task.assignee_id == user_id, cast(Task.status, String) == TaskStatus.IN_PROGRESS.value), 1), else_=0)).label('my_new_active')
        ).filter(
            Task.project_id.in_(accessible_projects_subquery),
            Task.created_at >= thirty_days_ago
        ).first()

        new_active_tasks = task_creation_stats.new_active if task_creation_stats and task_creation_stats.new_active else 0
        my_new_active_tasks = task_creation_stats.my_new_active if task_creation_stats and task_creation_stats.my_new_active else 0
        
        # Active Tasks Change
        previous_in_progress = in_progress_tasks - new_active_tasks + tasks_completed_last_30_days
        active_tasks_change = self._calculate_percentage_change(in_progress_tasks, previous_in_progress)

        # Pending Review Change
        previous_pending = pending_review_tasks - my_new_active_tasks + my_completed_last_30_days
        pending_change = self._calculate_percentage_change(pending_review_tasks, previous_pending)

        # Team Velocity Change
        velocity_change = self._calculate_percentage_change(team_velocity_val, prev_velocity_val)
        
        return {
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
            "teamVelocityChange": self._format_change(velocity_change, is_percentage_point=True),
            "teamVelocityTrend": "up" if velocity_change >= 0 else "down"
        }

    def get_recent_projects(self, user_id: uuid.UUID, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent projects with progress stats."""
        accessible_projects_subquery = self._get_accessible_projects_query(user_id)
        
        project_stats = self.db.query(
            Task.project_id,
            func.count(Task.id).label('total_tasks'),
            func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed_tasks')
        ).filter(
            Task.project_id.in_(accessible_projects_subquery)
        ).group_by(Task.project_id).subquery()
        
        recent_projects_data = self.db.query(
            Project, 
            func.coalesce(project_stats.c.total_tasks, 0).label('total_tasks'),
            func.coalesce(project_stats.c.completed_tasks, 0).label('completed_tasks')
        ).outerjoin(
            project_stats, Project.id == project_stats.c.project_id
        ).filter(
            Project.id.in_(accessible_projects_subquery)
        ).order_by(desc(Project.updated_at)).limit(limit).all()
        
        result = []
        for project, p_total, p_completed in recent_projects_data:
            progress = round((p_completed / p_total * 100)) if p_total > 0 else 0
            result.append({
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "progress": progress,
                "color": "#6366f1",
                "updated_at": project.updated_at.isoformat() if project.updated_at else None
            })
        return result

    def get_recent_activities(self, user_id: uuid.UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent team activities."""
        accessible_projects_subquery = self._get_accessible_projects_query(user_id)
        
        activities_query = self.db.query(TaskHistory).options(
            joinedload(TaskHistory.user),
            joinedload(TaskHistory.project),
            joinedload(TaskHistory.task)
        ).filter(
            TaskHistory.project_id.in_(accessible_projects_subquery)
        ).order_by(desc(TaskHistory.timestamp)).limit(limit).all()
        
        result = []
        for activity in activities_query:
            # Format action text
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
            
            activity_type_str = activity.activity_type.value if hasattr(activity.activity_type, 'value') else str(activity.activity_type)
            action = action_map.get(activity_type_str, "performed action")
            
            result.append({
                "id": str(activity.id),
                "user": {
                    "name": activity.user.name if activity.user else "Unknown User", 
                    "id": str(activity.user_id),
                    "avatar": activity.user.avatar_url if activity.user else None
                },
                "action": action,
                "target": activity.task.title if activity.task else (activity.project.name if activity.project else "Unknown Target"),
                "time": activity.timestamp.isoformat() if activity.timestamp else None,
                "project": {
                    "name": activity.project.name if activity.project else "Unknown Project",
                    "id": str(activity.project_id) if activity.project else None
                } if activity.project else "Unknown Project" # Keep consistency with prev implementation which might have returned string or object
            })
            
            # Note: The original implementation had inconsistency in "project" field.
            # In /overview it returned project name string. In /team-activity it returned object.
            # I will normalize this in the router if needed, or stick to what is expected.
            # Looking at router: 
            # /overview: "project": activity.project.name ...
            # /team-activity: "project": { "name": ..., "id": ... }
            # I'll create separate methods or just handle it in the response mapping if it varies.
            # For now, I'll return the richer object, and let the router format it down if needed.
            
        return result

    def _calculate_percentage_change(self, current: float, previous: float) -> float:
        if previous > 0:
            return ((current - previous) / previous) * 100
        return 100 if current > 0 else 0

    def _format_change(self, val: float, is_percentage_point: bool = False) -> str:
        prefix = "+" if val >= 0 else ""
        suffix = "%"
        return f"{prefix}{round(val, 1)}{suffix}"
