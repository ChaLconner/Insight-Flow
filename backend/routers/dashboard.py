"""
Dashboard router for overview analytics and statistics.
"""
from typing import Any, List, Set
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, cast, String, case, and_, or_
from models.user import User
from models.project import Project, ProjectMember
from models.task import Task, TaskStatus
from models.task_history import TaskHistory, ActivityType
from database import get_db
from routers.auth import get_current_active_user
from utils.logger import setup_logger

logger = setup_logger("dashboard_router")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/overview")
def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get dashboard overview with statistics and recent activities.
    """
    try:
        from sqlalchemy import distinct
        
        # Defines the scope of projects: Owned by user OR User is a member
        # We use a subquery construct that can be used in IN clauses
        # This prevents fetching thousands of IDs into application memory
        accessible_projects_subquery = db.query(Project.id).outerjoin(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(
            or_(
                Project.owner_id == current_user.id,
                ProjectMember.user_id == current_user.id
            )
        )

        # Get statistics
        # 1. Total Projects
        total_projects = db.query(func.count(distinct(Project.id))).outerjoin(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(
            or_(
                Project.owner_id == current_user.id,
                ProjectMember.user_id == current_user.id
            )
        ).scalar() or 0
        
        if total_projects == 0:
            return {
                "stats": {
                    "totalProjects": 0, "totalProjectsChange": "+0%", "totalProjectsTrend": "up",
                    "totalTasks": 0, "completedTasks": 0,
                    "inProgressTasks": 0, "inProgressTasksChange": "+0%", "inProgressTasksTrend": "up",
                    "pendingReviewTasks": 0, "pendingReviewTasksChange": "+0%", "pendingReviewTasksTrend": "up",
                    "teamVelocity": 0, "teamVelocityChange": "+0%", "teamVelocityTrend": "up"
                },
                "recentProjects": [],
                "recentActivities": []
            }
            
        # Aggregate task statistics in a single query
        task_stats = db.query(
            func.count(Task.id).label('total'),
            func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed'),
            func.sum(case((cast(Task.status, String) == TaskStatus.IN_PROGRESS.value, 1), else_=0)).label('in_progress'),
            func.sum(case((and_(
                Task.assignee_id == current_user.id, 
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
        team_velocity = round((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
        
        # Get recent projects (last 5) with stats using query
        # Subquery for project stats within the accessible scope
        project_stats = db.query(
            Task.project_id,
            func.count(Task.id).label('total_tasks'),
            func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed_tasks')
        ).filter(
            Task.project_id.in_(accessible_projects_subquery)
        ).group_by(Task.project_id).subquery()
        
        # Main query for recent projects
        recent_projects_data = db.query(
            Project, 
            func.coalesce(project_stats.c.total_tasks, 0).label('total_tasks'),
            func.coalesce(project_stats.c.completed_tasks, 0).label('completed_tasks')
        ).outerjoin(
            project_stats, Project.id == project_stats.c.project_id
        ).filter(
            Project.id.in_(accessible_projects_subquery)
        ).order_by(desc(Project.updated_at)).limit(5).all()
        
        recent_projects = []
        for project, p_total, p_completed in recent_projects_data:
            progress = round((p_completed / p_total * 100)) if p_total > 0 else 0
            recent_projects.append({
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "progress": progress,
                "color": "#6366f1",  # Default color
                "updated_at": project.updated_at.isoformat() if project.updated_at else None
            })
        
        # Get recent activities
        recent_activities_query = db.query(TaskHistory).options(
            joinedload(TaskHistory.user),
            joinedload(TaskHistory.project),
            joinedload(TaskHistory.task)
        ).filter(
            TaskHistory.project_id.in_(accessible_projects_subquery)
        ).order_by(desc(TaskHistory.timestamp)).limit(10).all()
        
        recent_activities = []
        for activity in recent_activities_query:
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
            
            recent_activities.append({
                "id": str(activity.id),
                "user": {
                    "name": activity.user.name if activity.user else "Unknown User", 
                    "id": str(activity.user_id),
                    "avatar": activity.user.avatar_url if activity.user else None
                },
                "action": action,
                "time": activity.timestamp.isoformat() if activity.timestamp else None,
                "project": activity.project.name if activity.project else "Unknown Project"
            })
            
        # Calculate trends
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
        
        # 1. Total Projects Change
        projects_created_last_30_days = db.query(Project).filter(
            Project.id.in_(accessible_projects_subquery),
            Project.created_at >= thirty_days_ago
        ).count()
        
        previous_total_projects = total_projects - projects_created_last_30_days
        if previous_total_projects > 0:
            projects_change = ((total_projects - previous_total_projects) / previous_total_projects) * 100
        else:
            projects_change = 100 if total_projects > 0 else 0
            
        # Aggregate History Metrics for trends
        history_stats = db.query(
            func.sum(case((and_(TaskHistory.activity_type == ActivityType.TASK_COMPLETED, TaskHistory.timestamp >= thirty_days_ago), 1), else_=0)).label('completed_30d'),
            func.sum(case((and_(TaskHistory.user_id == current_user.id, TaskHistory.activity_type == ActivityType.TASK_COMPLETED, TaskHistory.timestamp >= thirty_days_ago), 1), else_=0)).label('my_completed_30d'),
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

        # Aggregate Task Creation Metrics (New Active Tasks)
        task_creation_stats = db.query(
            func.sum(case((cast(Task.status, String) == TaskStatus.IN_PROGRESS.value, 1), else_=0)).label('new_active'),
            func.sum(case((and_(Task.assignee_id == current_user.id, cast(Task.status, String) == TaskStatus.IN_PROGRESS.value), 1), else_=0)).label('my_new_active')
        ).filter(
            Task.project_id.in_(accessible_projects_subquery),
            Task.created_at >= thirty_days_ago
        ).first()

        new_active_tasks = task_creation_stats.new_active if task_creation_stats and task_creation_stats.new_active else 0
        my_new_active_tasks = task_creation_stats.my_new_active if task_creation_stats and task_creation_stats.my_new_active else 0
        
        # 2. Active Tasks Change (In Progress)
        previous_in_progress = in_progress_tasks - new_active_tasks + tasks_completed_last_30_days
        
        if previous_in_progress > 0:
            active_tasks_change = ((in_progress_tasks - previous_in_progress) / previous_in_progress) * 100
        else:
            active_tasks_change = 100 if in_progress_tasks > 0 else 0

        # 3. Pending Review Change (My In Progress Tasks)
        previous_pending = pending_review_tasks - my_new_active_tasks + my_completed_last_30_days
        
        if previous_pending > 0:
            pending_change = ((pending_review_tasks - previous_pending) / previous_pending) * 100
        else:
            pending_change = 100 if pending_review_tasks > 0 else 0

        # 4. Team Velocity (Tasks completed in last 7 days)
        if prev_velocity_val > 0:
            velocity_change = ((team_velocity_val - prev_velocity_val) / prev_velocity_val) * 100
        else:
            velocity_change = 100 if team_velocity_val > 0 else 0 
        
        def format_change(val, is_percentage_point=False):
            prefix = "+" if val >= 0 else ""
            suffix = "%"
            return f"{prefix}{round(val, 1)}{suffix}"

        return {
            "stats": {
                "totalProjects": total_projects,
                "totalProjectsChange": format_change(projects_change),
                "totalProjectsTrend": "up" if projects_change >= 0 else "down",
                
                "totalTasks": total_tasks,
                
                "completedTasks": completed_tasks,
                
                "inProgressTasks": in_progress_tasks,
                "inProgressTasksChange": format_change(active_tasks_change),
                "inProgressTasksTrend": "up" if active_tasks_change >= 0 else "down",
                
                "pendingReviewTasks": pending_review_tasks,
                "pendingReviewTasksChange": format_change(pending_change),
                "pendingReviewTasksTrend": "up" if pending_change >= 0 else "down",
                
                "teamVelocity": team_velocity_val,
                "teamVelocityChange": format_change(velocity_change, is_percentage_point=True),
                "teamVelocityTrend": "up" if velocity_change >= 0 else "down"
            },
            "recentProjects": recent_projects,
            "recentActivities": recent_activities
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard overview"
        )

@router.get("/today-tasks")
def get_today_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get tasks assigned to current user for today.
    """
    from datetime import datetime, date
    
    try:
        today = date.today()
        
        # Get tasks assigned to user due today or overdue
        tasks = db.query(Task).options(joinedload(Task.project)).filter(
            Task.assignee_id == current_user.id,
            (Task.due_date >= today) | (Task.due_date.is_(None))
        ).order_by(Task.due_date.asc()).limit(10).all()
        
        task_list = []
        for task in tasks:
            task_list.append({
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
                "priority": "medium",  # Default priority
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "project": {
                    "id": str(task.project.id) if task.project else None,
                    "name": task.project.name if task.project else "Unknown Project"
                }
            })
        
        return task_list
        
    except Exception as e:
        logger.error(f"Error getting today tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch today tasks"
        )

@router.get("/recent-projects")
def get_recent_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get recent projects for current user.
    """
    try:
        # Accessible projects subquery
        accessible_projects_subquery = db.query(Project.id).outerjoin(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(
            or_(
                Project.owner_id == current_user.id,
                ProjectMember.user_id == current_user.id
            )
        )
            
        # Subquery for project stats
        project_stats = db.query(
            Task.project_id,
            func.count(Task.id).label('total_tasks'),
            func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed_tasks')
        ).filter(
            Task.project_id.in_(accessible_projects_subquery)
        ).group_by(Task.project_id).subquery()
        
        # Main query
        projects_data = db.query(
            Project, 
            func.coalesce(project_stats.c.total_tasks, 0).label('total_tasks'),
            func.coalesce(project_stats.c.completed_tasks, 0).label('completed_tasks')
        ).outerjoin(
            project_stats, Project.id == project_stats.c.project_id
        ).filter(
            Project.id.in_(accessible_projects_subquery)
        ).order_by(desc(Project.updated_at)).limit(5).all()
        
        project_list = []
        for project, p_total, p_completed in projects_data:
            progress = round((p_completed / p_total * 100)) if p_total > 0 else 0
            
            project_list.append({
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "color": "#6366f1",  # Default color
                "progress": progress,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None
            })
        
        return project_list
        
    except Exception as e:
        logger.error(f"Error getting recent projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recent projects"
        )

@router.get("/team-activity")
def get_team_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get recent team activity.
    """
    try:
        # Accessible projects subquery
        accessible_projects_subquery = db.query(Project.id).outerjoin(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(
            or_(
                Project.owner_id == current_user.id,
                ProjectMember.user_id == current_user.id
            )
        )

        # Get recent activities
        recent_activities_query = db.query(TaskHistory).options(
            joinedload(TaskHistory.user),
            joinedload(TaskHistory.project),
            joinedload(TaskHistory.task)
        ).filter(
            TaskHistory.project_id.in_(accessible_projects_subquery)
        ).order_by(desc(TaskHistory.timestamp)).limit(20).all()
        
        recent_activities = []
        for activity in recent_activities_query:
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
            
            recent_activities.append({
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
                }
            })
            
        return recent_activities
        
    except Exception as e:
        logger.error(f"Error getting team activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team activity"
        )