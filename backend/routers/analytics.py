"""
Analytics router for project metrics and productivity data.
"""
from typing import List, Dict, Any, TYPE_CHECKING
import uuid
import json
from collections import defaultdict

if TYPE_CHECKING:
    pass
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from services.project_service import ProjectService
from services.analytics_service import AnalyticsService
from services.task_history_service import TaskHistoryService
from database import get_db
from routers.auth import get_current_active_user
from models.user import User
from dependencies import require_project_member
from models.project import Project
from utils.logger import setup_logger
from schemas.analytics import (
    ActivityResponse, 
    BatchActivityResponse, 
    AnalyticsOverviewResponse,
    BatchActivityRequest
)

# Create router instance
router = APIRouter()

# Setup logger
logger = setup_logger(__name__)

@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get global analytics overview for the current user across all projects.
    """
    analytics_service = AnalyticsService(db)
    # The service returns a dict that matches the AnalyticsOverviewResponse structure
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

@router.get("/projects/{project_id}/activity", response_model=Dict[str, Any])
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
    task_history_service = TaskHistoryService(db)
    
    # Get actual activity from database
    activities = task_history_service.get_recent_activities(project.id, limit)
    
    # Batch fetch users to avoid N+1
    user_ids = {activity.user_id for activity in activities}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}
    
    # Format activities for frontend
    formatted_activities = []
    for activity in activities:
        # Get user info from map
        user = user_map.get(activity.user_id)
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

@router.get("/activity", response_model=Dict[str, Any])
def get_all_recent_activity(
    limit: int = Query(20, description="Number of activities to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get recent activity across all projects the user has access to.
    """
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

@router.post("/activity/batch", response_model=List[BatchActivityResponse])
def get_batch_recent_activity(
    request: BatchActivityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[Any]:
    """
    Get recent activity for multiple projects in batch.
    Optimized to avoid N+1 queries.
    """
    project_ids_str = request.project_ids
    limit = request.limit
    
    if not project_ids_str:
        return []
    
    project_service = ProjectService(db)
    task_history_service = TaskHistoryService(db)
    
    # 1. Validate UUIDs and filter valid ones
    valid_project_uuids = []
    results_map: Dict[str, Dict[str, Any]] = {}
    
    for pid in project_ids_str:
        try:
            valid_project_uuids.append(uuid.UUID(pid))
        except ValueError:
            results_map[pid] = {
                "projectId": pid,
                "error": "Invalid project ID format"
            }
            
    if not valid_project_uuids:
        return list(results_map.values())

    # 2. Bulk check permissions
    # Get all projects the user has access to that match the requested IDs
    user_projects = project_service.get_projects(user_id=uuid.UUID(str(current_user.id)))
    accessible_project_ids = {p.id for p in user_projects}
    
    # Identify which of the requested valid UUIDs are actually accessible
    accessible_requested_uuids = []
    for pid in valid_project_uuids:
        if pid in accessible_project_ids:
            accessible_requested_uuids.append(pid)
        else:
            results_map[str(pid)] = {
                "projectId": str(pid),
                "error": "Project not found or access denied"
            }
            
    if not accessible_requested_uuids:
        return list(results_map.values())
        
    # 3. Batch fetch activities
    total_limit = limit * len(accessible_requested_uuids) * 2 # Safety buffer
    activities = task_history_service.get_recent_activities_for_projects(
        accessible_requested_uuids, 
        limit=total_limit
    )
    
    # 4. Group activities by project
    activities_by_project = defaultdict(list)
    user_ids_to_fetch = set()
    
    for activity in activities:
        pid_str = str(activity.project_id)
        # Enforce per-project limit in memory
        if len(activities_by_project[pid_str]) < limit:
            activities_by_project[pid_str].append(activity)
            user_ids_to_fetch.add(activity.user_id)
            
    # 5. Batch fetch users
    users = db.query(User).filter(User.id.in_(user_ids_to_fetch)).all()
    user_map = {u.id: u for u in users}
    
    # 6. Format results
    for pid in accessible_requested_uuids:
        pid_str = str(pid)
        if pid_str in results_map:
            continue # Already handled error
            
        project_activities = activities_by_project.get(pid_str, [])
        formatted_activities = []
        
        for activity in project_activities:
            user = user_map.get(activity.user_id)
            user_name = user.name if user else f"User {activity.user_id}"
            
            formatted_activity = {
                "id": str(activity.id),
                "type": activity.activity_type.value,
                "user_name": user_name,
                "task_title": activity.task_title,
                "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,
                "description": activity.description,
                "project_name": next((p.name for p in user_projects if p.id == activity.project_id), ""),
                "project_id": str(activity.project_id)
            }
            
            if activity.new_values:
                try:
                    new_values = json.loads(activity.new_values)
                    if "assignee_name" in new_values:
                        formatted_activity["assignee_name"] = new_values["assignee_name"]
                except (json.JSONDecodeError, TypeError):
                    pass
            
            formatted_activities.append(formatted_activity)
            
        results_map[pid_str] = {
            "projectId": pid_str,
            "activities": formatted_activities
        }
        
    # Return matched order if possible
    final_results = []
    for pid_str in project_ids_str:
        if pid_str in results_map:
            final_results.append(results_map[pid_str])
            
    return final_results