"""
Dashboard router for overview analytics and statistics.
"""
from typing import Any, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, cast, String
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
        # Get user's projects
        user_projects = db.query(Project).filter(
            Project.owner_id == current_user.id
        ).all()
        
        # Get projects where user is a member
        member_projects = db.query(Project).join(ProjectMember).filter(
            ProjectMember.user_id == current_user.id
        ).all()
        
        # Combine unique projects
        all_project_ids = set([p.id for p in user_projects] + [p.id for p in member_projects])
        
        # Get statistics
        total_projects = len(all_project_ids)
        
        # Get total tasks across all projects
        total_tasks = db.query(Task).filter(
            Task.project_id.in_(all_project_ids)
        ).count() if all_project_ids else 0
        
        # Get completed tasks
        completed_tasks = db.query(Task).filter(
            Task.project_id.in_(all_project_ids),
            cast(Task.status, String) == TaskStatus.DONE.value
        ).count() if all_project_ids else 0
        
        # Get in progress tasks
        in_progress_tasks = db.query(Task).filter(
            Task.project_id.in_(all_project_ids),
            cast(Task.status, String) == TaskStatus.IN_PROGRESS.value
        ).count() if all_project_ids else 0
        
        # Get pending review tasks (tasks assigned to user)
        pending_review_tasks = db.query(Task).filter(
            Task.assignee_id == current_user.id,
            cast(Task.status, String) == TaskStatus.IN_PROGRESS.value
        ).count()
        
        # Calculate team velocity (percentage of completed tasks)
        team_velocity = round((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
        
        # Get recent projects (last 5)
        recent_projects_query = db.query(Project).filter(
            Project.id.in_(all_project_ids)
        ).order_by(desc(Project.updated_at)).limit(5)
        
        recent_projects = []
        for project in recent_projects_query.all():
            # Get project statistics
            project_tasks = db.query(Task).filter(Task.project_id == project.id).count()
            project_completed = db.query(Task).filter(
                Task.project_id == project.id,
                cast(Task.status, String) == TaskStatus.DONE.value
            ).count()
            
            progress = round((project_completed / project_tasks * 100)) if project_tasks > 0 else 0
            
            recent_projects.append({
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "progress": progress,
                "color": "#6366f1",  # Default color
                "updated_at": project.updated_at.isoformat() if project.updated_at else None
            })
        
        # Get recent activities
        recent_activities_query = db.query(TaskHistory).filter(
            TaskHistory.project_id.in_(all_project_ids)
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
        
        # 1. Total Projects Change
        projects_created_last_30_days = db.query(Project).filter(
            Project.id.in_(all_project_ids),
            Project.created_at >= thirty_days_ago
        ).count()
        
        previous_total_projects = total_projects - projects_created_last_30_days
        if previous_total_projects > 0:
            projects_change = ((total_projects - previous_total_projects) / previous_total_projects) * 100
        else:
            projects_change = 100 if total_projects > 0 else 0
            
        # 2. Active Tasks Change (In Progress)
        tasks_completed_last_30_days = db.query(TaskHistory).filter(
            TaskHistory.project_id.in_(all_project_ids),
            TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
            TaskHistory.timestamp >= thirty_days_ago
        ).count()
        
        new_active_tasks = db.query(Task).filter(
            Task.project_id.in_(all_project_ids),
            cast(Task.status, String) == TaskStatus.IN_PROGRESS.value,
            Task.created_at >= thirty_days_ago
        ).count()
        
        previous_in_progress = in_progress_tasks - new_active_tasks + tasks_completed_last_30_days
        
        if previous_in_progress > 0:
            active_tasks_change = ((in_progress_tasks - previous_in_progress) / previous_in_progress) * 100
        else:
            active_tasks_change = 100 if in_progress_tasks > 0 else 0

        # 3. Pending Review Change (My In Progress Tasks)
        my_completed_last_30_days = db.query(TaskHistory).filter(
            TaskHistory.project_id.in_(all_project_ids),
            TaskHistory.user_id == current_user.id,
            TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
            TaskHistory.timestamp >= thirty_days_ago
        ).count()
        
        my_new_active_tasks = db.query(Task).filter(
            Task.assignee_id == current_user.id,
            cast(Task.status, String) == TaskStatus.IN_PROGRESS.value,
            Task.created_at >= thirty_days_ago
        ).count()
        
        previous_pending = pending_review_tasks - my_new_active_tasks + my_completed_last_30_days
        
        if previous_pending > 0:
            pending_change = ((pending_review_tasks - previous_pending) / previous_pending) * 100
        else:
            pending_change = 100 if pending_review_tasks > 0 else 0

        # 4. Team Velocity (Tasks completed in last 7 days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
        
        team_velocity = db.query(TaskHistory).filter(
            TaskHistory.project_id.in_(all_project_ids),
            TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
            TaskHistory.timestamp >= seven_days_ago
        ).count()
        
        prev_velocity = db.query(TaskHistory).filter(
            TaskHistory.project_id.in_(all_project_ids),
            TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
            TaskHistory.timestamp >= fourteen_days_ago,
            TaskHistory.timestamp < seven_days_ago
        ).count()
        
        if prev_velocity > 0:
            velocity_change = ((team_velocity - prev_velocity) / prev_velocity) * 100
        else:
            velocity_change = 100 if team_velocity > 0 else 0 
        
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
                
                "teamVelocity": team_velocity,
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
        tasks = db.query(Task).filter(
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
        # Get user's projects
        user_projects = db.query(Project).filter(
            Project.owner_id == current_user.id
        ).order_by(desc(Project.updated_at)).limit(5).all()
        
        # Get projects where user is a member
        member_projects = db.query(Project).join(ProjectMember).filter(
            ProjectMember.user_id == current_user.id
        ).order_by(desc(Project.updated_at)).limit(5).all()
        
        # Combine and deduplicate
        all_projects = {}
        for project in user_projects + member_projects:
            if project.id not in all_projects:
                all_projects[project.id] = project
        
        # Convert to response format
        project_list = []
        for project in list(all_projects.values())[:5]:
            # Get project statistics
            project_tasks = db.query(Task).filter(Task.project_id == project.id).count()
            project_completed = db.query(Task).filter(
                Task.project_id == project.id,
                cast(Task.status, String) == TaskStatus.DONE.value
            ).count()
            
            progress = round((project_completed / project_tasks * 100)) if project_tasks > 0 else 0
            
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
        # Get user's projects
        user_projects = db.query(Project).filter(
            Project.owner_id == current_user.id
        ).all()
        
        # Get projects where user is a member
        member_projects = db.query(Project).join(ProjectMember).filter(
            ProjectMember.user_id == current_user.id
        ).all()
        
        # Combine unique projects
        all_project_ids = set([p.id for p in user_projects] + [p.id for p in member_projects])
        
        if not all_project_ids:
            return []

        # Get recent activities
        recent_activities_query = db.query(TaskHistory).filter(
            TaskHistory.project_id.in_(all_project_ids)
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