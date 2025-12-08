"""
Analytics router for project metrics and productivity data.
"""
from typing import List, Dict, Any, TYPE_CHECKING
import uuid
import json

if TYPE_CHECKING:
    pass
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from services.project_service import ProjectService
from services.analytics_service import AnalyticsService
from database import get_db
from routers.auth import get_current_active_user
from models.user import User
from dependencies import require_project_member
from models.project import Project
from utils.logger import setup_logger

# Create router instance
router = APIRouter()

# Setup logger
logger = setup_logger(__name__)

@router.get("/overview")
def get_analytics_overview(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get global analytics overview for the current user across all projects.
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_user_analytics_overview(current_user.id, period=period)

@router.get("/projects/{project_id}/dashboard")
def get_dashboard_metrics(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project: Project = Depends(require_project_member)
) -> Dict[str, Any]:
    """
    Get dashboard metrics for a project.
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_project_dashboard_stats(project.id)

@router.get("/projects/{project_id}/productivity")
def get_productivity_data(
    project_id: str,
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
    group_by: str = Query("week", description="Group by: day, week, month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project: Project = Depends(require_project_member)
) -> Dict[str, Any]:
    """
    Get productivity data for a project.
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_project_productivity(project.id, period=period, group_by=group_by)

@router.get("/projects/{project_id}/contributions")
def get_contributions(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project: Project = Depends(require_project_member)
) -> Dict[str, Any]:
    """
    Get team contributions for a project.
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_project_contributions(project.id)

@router.get("/projects/{project_id}/activity")
def get_recent_activity(
    project_id: str,
    limit: int = Query(10, description="Number of activities to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project: Project = Depends(require_project_member)
) -> Dict[str, Any]:
    """
    Get recent activity for a project.
    """
    # Keeps using TaskHistoryService directly or could move to AnalyticsService if preferred.
    # For now, let's keep it here but clean up imports
    from services.task_history_service import TaskHistoryService
    
    task_history_service = TaskHistoryService(db)
    
    # Get actual activity from database
    activities = task_history_service.get_recent_activities(project.id, limit)
    
    # Format activities for frontend
    formatted_activities = []
    for activity in activities:
        # Get user info
        user = db.query(User).filter(User.id == activity.user_id).first()
        user_name = user.name if user else f"User {activity.user_id}"
        
        formatted_activity = {
            "id": str(activity.id),
            "type": activity.activity_type.value,
            "user_name": user_name,
            "task_title": activity.task_title,
            "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,
            "description": activity.description,
            "project_name": project.name,
            "project_id": str(project.id)
        }
        
        # Add additional context for specific activity types
        if activity.new_values:
            try:
                new_values = json.loads(activity.new_values)
                if "assignee_name" in new_values:
                    formatted_activity["assignee_name"] = new_values["assignee_name"]
            except (json.JSONDecodeError, TypeError):
                pass
        
        formatted_activities.append(formatted_activity)
    
    return {
        "activities": formatted_activities,
        "total_count": len(formatted_activities)
    }

@router.get("/activity")
def get_all_recent_activity(
    limit: int = Query(20, description="Number of activities to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get recent activity across all projects the user has access to.
    """
    from services.task_history_service import TaskHistoryService
    
    project_service = ProjectService(db)
    task_history_service = TaskHistoryService(db)
    
    # Get all projects the user has access to (owner or member)
    user_projects = project_service.get_projects(user_id=uuid.UUID(str(current_user.id)))
    project_ids = [p.id for p in user_projects]
    
    if not project_ids:
        return {
            "activities": [],
            "total_count": 0
        }
    
    # Get activities from all accessible projects
    activities = task_history_service.get_recent_activities_for_projects(project_ids, limit)

    # Batch fetch users to avoids N+1
    user_ids = {activity.user_id for activity in activities}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}
    
    # Project map for quick lookup
    project_map = {p.id: p for p in user_projects}

    all_activities = []
    for activity in activities:
        # Get user info from map
        user = user_map.get(activity.user_id)
        user_name = user.name if user else f"User {activity.user_id}"
        
        # Get project info from map
        project = project_map.get(activity.project_id)
        project_name = project.name if project else "Unknown Project"
        
        formatted_activity = {
            "id": str(activity.id),
            "type": activity.activity_type.value,
            "user_name": user_name,
            "task_title": activity.task_title,
            "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,
            "description": activity.description,
            "project_name": project_name,
            "project_id": str(activity.project_id)
        }
        
        # Add additional context for specific activity types
        if activity.new_values:
            try:
                new_values = json.loads(activity.new_values)
                if "assignee_name" in new_values:
                    formatted_activity["assignee_name"] = new_values["assignee_name"]
            except (json.JSONDecodeError, TypeError):
                pass
        
        all_activities.append(formatted_activity)
    
    return {
        "activities": all_activities,
        "total_count": len(all_activities)
    }

@router.post("/activity/batch")
def get_batch_recent_activity(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """
    Get recent activity for multiple projects in batch.
    """
    from services.task_history_service import TaskHistoryService
    
    project_ids = request.get("project_ids", [])
    limit = request.get("limit", 10)
    
    if not project_ids:
        return []
    
    project_service = ProjectService(db)
    task_history_service = TaskHistoryService(db)
    
    results: List[Dict[str, Any]] = []
    
    for project_id_str in project_ids:
        try:
            project_uuid = uuid.UUID(project_id_str)
        except ValueError:
            results.append({
                "projectId": project_id_str,
                "error": "Invalid project ID format"
            })
            continue
        
        try:
            # Check if user has access to this project
            project = project_service.get_project_by_id(project_uuid)
            if not project:
                results.append({
                    "projectId": project_id_str,
                    "error": "Project not found"
                })
                continue
            
            is_owner = project.owner_id == uuid.UUID(str(current_user.id))
            is_member = project_service.is_project_member(project_uuid, uuid.UUID(str(current_user.id)))
            
            if not is_owner and not is_member:
                results.append({
                    "projectId": project_id_str,
                    "error": "Not a member of this project"
                })
                continue
            
            # Get activities for this project
            activities = task_history_service.get_recent_activities(project_uuid, limit)
            
            # Format activities
            formatted_activities = []
            for activity in activities:
                # Get user info
                user = db.query(User).filter(User.id == activity.user_id).first()
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
                
                formatted_activities.append(formatted_activity)
            
            results.append({
                "projectId": project_id_str,
                "activities": formatted_activities
            })
            
        except Exception as e:
            logger.error(f"Error processing project {project_id_str}: {e}")
            results.append({
                "projectId": project_id_str,
                "error": str(e)
            })
    
    return results