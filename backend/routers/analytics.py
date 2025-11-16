"""
Analytics router for project metrics and productivity data.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from services.project_service import ProjectService
from database import get_db
from routers.auth import get_current_active_user
from models.user import User
from dependencies import get_project_member
from utils.logger import setup_logger
import uuid

logger = setup_logger("analytics_router")

router = APIRouter(tags=["analytics"])

@router.get("/projects/{project_id}/dashboard")
def get_dashboard_metrics(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_uuid: uuid.UUID = Depends(get_project_member)
) -> Dict[str, Any]:
    """
    Get dashboard metrics for a project.
    """
    
    
    # Get actual project metrics
    from models.task import Task
    from models.project import ProjectMember
    
    # Task statistics
    total_tasks = db.query(Task).filter(Task.project_id == project_uuid).count()
    completed_tasks = db.query(Task).filter(
        Task.project_id == project_uuid,
        Task.status == 'done'
    ).count()
    todo_tasks = db.query(Task).filter(
        Task.project_id == project_uuid,
        Task.status == 'todo'
    ).count()
    in_progress_tasks = db.query(Task).filter(
        Task.project_id == project_uuid,
        Task.status == 'in_progress'
    ).count()
    
    # Member statistics
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_uuid).all()
    
    # Get actual recent activity from database
    from services.task_history_service import TaskHistoryService
    task_history_service = TaskHistoryService(db)
    
    # Get recent activities from database
    activities = task_history_service.get_recent_activities(project_uuid, 10)
    
    # Format activities for frontend
    recent_activity = []
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
                import json
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

@router.get("/projects/{project_id}/productivity")
def get_productivity_data(
    project_id: str,
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
    group_by: str = Query("week", description="Group by: day, week, month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_uuid: uuid.UUID = Depends(get_project_member)
) -> Dict[str, Any]:
    """
    Get productivity data for a project.
    """
    
    logger.info(f"[DEBUG] get_productivity_data called:")
    logger.info(f"[DEBUG] - project_id: {project_id}")
    logger.info(f"[DEBUG] - period: {period}")
    logger.info(f"[DEBUG] - group_by: {group_by}")
    logger.info(f"[DEBUG] - project_uuid: {project_uuid}")
    logger.info(f"[DEBUG] - current_user: {current_user.id}")
    
    try:
        from models.task import Task
        from datetime import datetime, timedelta, timezone
        import random
        
        # Calculate date range based on period - use timezone-aware datetimes
        end_date = datetime.now(timezone.utc)
        logger.info(f"[DEBUG] end_date: {end_date}")
        if period == '7d':
            start_date = end_date - timedelta(days=7)
            days = 7
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
            days = 30
        else:  # 90d
            start_date = end_date - timedelta(days=90)
            days = 90
        
        logger.info(f"[DEBUG] start_date: {start_date}, days: {days}")
        
        # Get tasks in date range using the project_uuid from dependency
        try:
            tasks = db.query(Task).filter(
                Task.project_id == project_uuid,
                Task.created_at >= start_date,
                Task.created_at.isnot(None)
            ).all()
            logger.info(f"[DEBUG] Found {len(tasks)} tasks in date range")
        except Exception as e:
            logger.error(f"[DEBUG] Error querying tasks: {e}")
            raise
        
        # Group by day
        productivity_data = []
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            next_date = current_date + timedelta(days=1)
            
            day_tasks = [t for t in tasks if t.created_at and current_date <= t.created_at < next_date]
            
            created_count = len(day_tasks)
            completed_count = len([t for t in day_tasks if t.status == 'done'])
            
            productivity_data.append({
                "date": current_date.isoformat(),
                "created_tasks": created_count,
                "completed_tasks": completed_count
            })
        
        logger.info(f"[DEBUG] Generated {len(productivity_data)} data points")
        
        result = {
            "period": period,
            "group_by": group_by,
            "data": productivity_data
        }
        
        logger.info(f"[DEBUG] Returning result with {len(productivity_data)} data points")
        return result
        
    except Exception as e:
        logger.error(f"[DEBUG] Unexpected error in get_productivity_data: {e}")
        logger.error(f"[DEBUG] Error type: {type(e)}")
        import traceback
        logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise

@router.get("/projects/{project_id}/contributions")
def get_contributions(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get team contributions for a project.
    """
    
    
    from models.task import Task, TaskStatus
    from models.user import User
    from models.project import ProjectMember
    from sqlalchemy import func, distinct
    from sqlalchemy.orm import aliased
    
    # Convert project_id to UUID
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Alias for tasks created by a member
    CreatedTask = aliased(Task)
    # Alias for tasks assigned to and completed by a member
    CompletedTask = aliased(Task)
    # Alias for tasks assigned to a member (total assigned)
    AssignedTask = aliased(Task)

    contributions_query = db.query(
        User.id,
        User.name,
        func.count(distinct(CreatedTask.id)).label('tasks_created'),
        func.count(distinct(CompletedTask.id)).label('tasks_completed'),
        func.count(distinct(AssignedTask.id)).label('total_assigned')
    ).join(
        ProjectMember, User.id == ProjectMember.user_id
    ).outerjoin(
        CreatedTask,
        (CreatedTask.project_id == project_uuid) & (CreatedTask.created_by == User.id)
    ).outerjoin(
        CompletedTask,
        (CompletedTask.project_id == project_uuid) & (CompletedTask.assignee_id == User.id) & (CompletedTask.status == 'done')
    ).outerjoin(
        AssignedTask,
        (AssignedTask.project_id == project_uuid) & (AssignedTask.assignee_id == User.id)
    ).filter(
        ProjectMember.project_id == project_uuid
    ).group_by(
        User.id, User.name
    ).all()
    
    contributions = []
    for user_id, user_name, tasks_created, tasks_completed, total_assigned in contributions_query:
        completion_rate = tasks_completed / max(total_assigned, 1) if total_assigned > 0 else 0.0
        contributions.append({
            "user_id": str(user_id),
            "name": user_name,
            "avatar_url": None,  # Could be added later
            "tasks_created": tasks_created,
            "tasks_completed": tasks_completed,
            "completion_rate": completion_rate
        })
    
    return {
        "project_id": project_uuid,
        "contributions": contributions
    }

@router.get("/projects/{project_id}/activity")
def get_recent_activity(
    project_id: str,
    limit: int = Query(10, description="Number of activities to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get recent activity for a project.
    """
    from services.task_history_service import TaskHistoryService
    from models.user import User
    
    # Add detailed logging for debugging
    logger.info(f"[DEBUG] get_recent_activity called:")
    logger.info(f"[DEBUG] - project_id: {project_id}")
    logger.info(f"[DEBUG] - limit: {limit}")
    logger.info(f"[DEBUG] - current_user: {current_user.id} ({current_user.email})")
    
    project_service = ProjectService(db)
    task_history_service = TaskHistoryService(db)
    
    try:
        project_uuid = uuid.UUID(project_id)
        logger.info(f"[DEBUG] Successfully parsed UUID: {project_uuid}")
    except ValueError as e:
        logger.error(f"[DEBUG] Invalid UUID format: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Check if user is owner or member of project
    project = project_service.get_project_by_id(project_uuid)
    if not project:
        logger.error(f"[DEBUG] Project not found: {project_uuid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    logger.info(f"[DEBUG] Found project: {project.name}, owner: {project.owner_id}")
    logger.info(f"[DEBUG] Current user is owner: {project.owner_id == current_user.id}")
    
    # Allow access if user is owner or member
    is_member = project_service.is_project_member(project_uuid, current_user.id)
    logger.info(f"[DEBUG] User membership check result: {is_member}")
    
    if project.owner_id != current_user.id and not is_member:
        logger.error(f"[DEBUG] User {current_user.id} is not a member of project {project_uuid}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    logger.info(f"[DEBUG] User {current_user.id} has access to project {project_uuid}")
    
    # Get actual activity from database
    logger.info(f"[DEBUG] Calling task_history_service.get_recent_activities...")
    activities = task_history_service.get_recent_activities(project_uuid, limit)
    logger.info(f"[DEBUG] Retrieved {len(activities)} activities from database")
    
    # Get project information
    project_name = project.name if project else "Unknown Project"
    
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
            "project_name": project_name,
            "project_id": str(project_id)
        }
        
        # Add additional context for specific activity types
        if activity.new_values:
            import json
            try:
                new_values = json.loads(activity.new_values)
                if "assignee_name" in new_values:
                    formatted_activity["assignee_name"] = new_values["assignee_name"]
            except (json.JSONDecodeError, TypeError):
                pass
        
        formatted_activities.append(formatted_activity)
        logger.debug(f"[DEBUG] Formatted activity: {formatted_activity}")
    
    logger.info(f"[DEBUG] Returning {len(formatted_activities)} formatted activities")
    
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
    from models.user import User
    from models.project import Project
    
    logger.info(f"[DEBUG] get_all_recent_activity called:")
    logger.info(f"[DEBUG] - limit: {limit}")
    logger.info(f"[DEBUG] - current_user: {current_user.id} ({current_user.email})")
    
    project_service = ProjectService(db)
    task_history_service = TaskHistoryService(db)
    
    # Get all projects the user has access to (owner or member)
    user_projects = project_service.get_projects(user_id=current_user.id)
    project_ids = [p.id for p in user_projects]
    
    if not project_ids:
        return {
            "activities": [],
            "total_count": 0
        }
    
    logger.info(f"[DEBUG] User has access to {len(project_ids)} projects")
    
    # Get activities from all accessible projects
    all_activities = []
    for project_id in project_ids:
        try:
            activities = task_history_service.get_recent_activities(project_id, limit // len(project_ids) + 1)
            # Add project info to each activity
            project = next((p for p in user_projects if p.id == project_id), None)
            project_name = project.name if project else "Unknown Project"
            
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
                    "project_name": project_name,
                    "project_id": str(project_id)
                }
                
                # Add additional context for specific activity types
                if activity.new_values:
                    import json
                    try:
                        new_values = json.loads(activity.new_values)
                        if "assignee_name" in new_values:
                            formatted_activity["assignee_name"] = new_values["assignee_name"]
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                all_activities.append(formatted_activity)
        except Exception as e:
            logger.error(f"[DEBUG] Error getting activities for project {project_id}: {e}")
            continue
    
    # Sort by timestamp (most recent first) and limit
    all_activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    limited_activities = all_activities[:limit]
    
    logger.info(f"[DEBUG] Returning {len(limited_activities)} activities across all projects")
    
    return {
        "activities": limited_activities,
        "total_count": len(limited_activities)
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
    from models.user import User
    from models.project import Project
    
    project_ids = request.get("project_ids", [])
    limit = request.get("limit", 10)
    
    logger.info(f"[DEBUG] get_batch_recent_activity called:")
    logger.info(f"[DEBUG] - project_ids: {project_ids}")
    logger.info(f"[DEBUG] - limit: {limit}")
    logger.info(f"[DEBUG] - current_user: {current_user.id} ({current_user.email})")
    
    if not project_ids:
        return []
    
    project_service = ProjectService(db)
    task_history_service = TaskHistoryService(db)
    
    results = []
    
    for project_id_str in project_ids:
        try:
            project_uuid = uuid.UUID(project_id_str)
        except ValueError:
            logger.error(f"[DEBUG] Invalid project ID format: {project_id_str}")
            results.append({
                "projectId": project_id_str,
                "error": "Invalid project ID format"
            })
            continue
        
        try:
            # Check if user has access to this project
            project = project_service.get_project_by_id(project_uuid)
            if not project:
                logger.error(f"[DEBUG] Project not found: {project_uuid}")
                results.append({
                    "projectId": project_id_str,
                    "error": "Project not found"
                })
                continue
            
            is_owner = project.owner_id == current_user.id
            is_member = project_service.is_project_member(project_uuid, current_user.id)
            
            if not is_owner and not is_member:
                logger.error(f"[DEBUG] User {current_user.id} has no access to project {project_uuid}")
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
                    import json
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
            logger.error(f"[DEBUG] Error processing project {project_id_str}: {e}")
            results.append({
                "projectId": project_id_str,
                "error": str(e)
            })
    
    logger.info(f"[DEBUG] Batch activity request completed for {len(results)} projects")
    
    return results
