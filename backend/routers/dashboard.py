"""
Dashboard router for overview analytics and statistics.
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.user import User
from models.project import Project, ProjectMember
from models.task import Task, TaskStatus
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
            Task.status == TaskStatus.DONE
        ).count() if all_project_ids else 0
        
        # Get in progress tasks
        in_progress_tasks = db.query(Task).filter(
            Task.project_id.in_(all_project_ids),
            Task.status == TaskStatus.IN_PROGRESS
        ).count() if all_project_ids else 0
        
        # Get pending review tasks (tasks assigned to user)
        pending_review_tasks = db.query(Task).filter(
            Task.assignee_id == current_user.id,
            Task.status == TaskStatus.IN_PROGRESS
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
                Task.status == TaskStatus.DONE
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
        
        # Get recent activities (simplified - would need task history table for real implementation)
        recent_activities = [
            {
                "id": "1",
                "user": {"name": current_user.name, "id": str(current_user.id)},
                "action": "completed task",
                "target": "Sample Task",
                "timestamp": "2h ago"
            }
        ]
        
        return {
            "stats": {
                "totalProjects": total_projects,
                "totalTasks": total_tasks,
                "completedTasks": completed_tasks,
                "inProgressTasks": in_progress_tasks,
                "pendingReviewTasks": pending_review_tasks,
                "teamVelocity": team_velocity
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
                Task.status == TaskStatus.DONE
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