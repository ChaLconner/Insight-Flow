"""
Analytics router for project metrics and productivity data.
"""
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from services.project_service import ProjectService
from database import get_db
from routers.auth import get_current_active_user
from models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard/{project_id}")
def get_dashboard_metrics(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get dashboard metrics for a project.
    """
    import uuid
    project_service = ProjectService(db)
    
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Check if user is a member of project
    if not project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
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
    
    # Recent activity (mock data for now)
    recent_activity = [
        {
            "id": "1",
            "type": "task_completed",
            "user_name": "John Doe",
            "task_title": "Setup database schema",
            "timestamp": "2024-01-15T10:30:00Z"
        },
        {
            "id": "2",
            "type": "task_created",
            "user_name": "Jane Smith",
            "task_title": "Create API documentation",
            "timestamp": "2024-01-15T09:15:00Z"
        }
    ]
    
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

@router.get("/productivity/{project_id}")
def get_productivity_data(
    project_id: str,
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
    group_by: str = Query("week", description="Group by: day, week, month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get productivity data for a project.
    """
    import uuid
    project_service = ProjectService(db)
    
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Check if user is a member of project
    if not project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    from models.task import Task
    from datetime import datetime, timedelta
    import random
    
    # Calculate date range based on period
    end_date = datetime.utcnow()
    if period == '7d':
        start_date = end_date - timedelta(days=7)
        days = 7
    elif period == '30d':
        start_date = end_date - timedelta(days=30)
        days = 30
    else:  # 90d
        start_date = end_date - timedelta(days=90)
        days = 90
    
    # Get tasks in the date range
    tasks = db.query(Task).filter(
        Task.project_id == project_uuid,
        Task.created_at >= start_date
    ).all()
    
    # Group by day
    productivity_data = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        next_date = current_date + timedelta(days=1)
        
        day_tasks = [t for t in tasks if current_date <= t.created_at < next_date]
        
        created_count = len(day_tasks)
        completed_count = len([t for t in day_tasks if t.status == 'done'])
        
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

@router.get("/contributions/{project_id}")
def get_contributions(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get team contributions for a project.
    """
    import uuid
    project_service = ProjectService(db)
    
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Check if user is a member of project
    if not project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    from models.task import Task
    from models.user import User
    from models.project import ProjectMember
    from sqlalchemy import func
    
    # Get all members of the project
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_uuid).all()
    
    contributions = []
    for member in members:
        # Get user info
        user = db.query(User).filter(User.id == member.user_id).first()
        
        # Get task statistics for this member
        created_tasks = db.query(Task).filter(
            Task.project_id == project_uuid,
            Task.created_by == member.user_id
        ).count()
        
        completed_tasks = db.query(Task).filter(
            Task.project_id == project_uuid,
            Task.assignee_id == member.user_id,
            Task.status == 'done'
        ).count()
        
        total_assigned = db.query(Task).filter(
            Task.project_id == project_uuid,
            Task.assignee_id == member.user_id
        ).count()
        
        completion_rate = completed_tasks / max(total_assigned, 1)
        
        contributions.append({
            "user_id": str(member.user_id),
            "name": user.name if user else f"User {member.user_id}",
            "avatar_url": None,  # Could be added later
            "tasks_created": created_tasks,
            "tasks_completed": completed_tasks,
            "completion_rate": completion_rate
        })
    
    return {
        "project_id": project_uuid,
        "contributions": contributions
    }

@router.get("/activity/{project_id}")
def get_recent_activity(
    project_id: str,
    limit: int = Query(10, description="Number of activities to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get recent activity for a project.
    """
    import uuid
    from services.task_history_service import TaskHistoryService
    from models.user import User
    
    project_service = ProjectService(db)
    task_history_service = TaskHistoryService(db)
    
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid project ID format"
        )
    
    # Check if user is a member of project
    if not project_service.is_project_member(project_uuid, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    # Get actual activity from database
    activities = task_history_service.get_recent_activities(project_uuid, limit)
    
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
    
    return {
        "activities": formatted_activities,
        "total_count": len(formatted_activities)
    }