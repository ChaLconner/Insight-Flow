"""
Dashboard router for overview analytics and statistics.
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.user import User
from database import get_db
from routers.auth import get_current_active_user
from utils.logger import setup_logger
from services.dashboard_service import DashboardService

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
        service = DashboardService(db)
        
        # Get stats
        stats = service.get_overview_stats(current_user.id)
        
        # Get recent projects
        recent_projects = service.get_recent_projects(current_user.id, limit=5)
        
        # Get recent activities
        activities_data = service.get_recent_activities(current_user.id, limit=10)
        
        # Map activities to match overview response format (project name as string)
        recent_activities = []
        for activity in activities_data:
            # Handle potential variation in project data structure
            project_name = "Unknown Project"
            if isinstance(activity["project"], dict):
                project_name = activity["project"].get("name", "Unknown Project")
            elif isinstance(activity["project"], str):
                project_name = activity["project"]

            recent_activities.append({
                **activity,
                "project": project_name
            })

        return {
            "stats": stats,
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
    # Logic for today's tasks is simple and specific to this view, 
    # but we can move it to TaskService or DashboardService eventually.
    # For now, sticking to the review plan which focused on the massive overview logic.
    from datetime import date
    from models.task import Task
    from sqlalchemy.orm import joinedload
    
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
        service = DashboardService(db)
        return service.get_recent_projects(current_user.id, limit=5)
        
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
        service = DashboardService(db)
        # Service returns the detailed object structure required for this endpoint
        return service.get_recent_activities(current_user.id, limit=20)
        
    except Exception as e:
        logger.error(f"Error getting team activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team activity"
        )