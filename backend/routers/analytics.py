"""
Analytics router for project metrics and productivity data.
"""
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from services.project_service import ProjectService
from database import get_db
from routers.auth import get_current_active_user
from models.user import User
from dependencies import get_project_member
from utils.logger import setup_logger
import uuid
import json

# Create router instance
router = APIRouter()

# Setup logger
logger = setup_logger(__name__)

# Simple in-memory cache
from datetime import datetime, timedelta
_analytics_cache: Dict[str, Any] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

@router.get("/overview")
def get_analytics_overview(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get global analytics overview for the current user across all projects.
    Includes caching for performance (TTL: 5 minutes).
    """
    # Check cache
    cache_key = f"{current_user.id}:{period}"
    now = datetime.now()
    
    if cache_key in _analytics_cache:
        cached_ts, cached_data = _analytics_cache[cache_key]
        if (now - cached_ts).total_seconds() < CACHE_TTL_SECONDS:
            logger.info(f"Serving analytics from cache for user {current_user.id}")
            return cached_data
            
    from models.project import Project, ProjectMember
    from models.task import Task, TaskStatus
    from models.task_history import TaskHistory, ActivityType
    from sqlalchemy import func, case, distinct, and_, or_, cast, String, text, extract
    
    # Efficient Subquery for accessible projects
    accessible_projects_subquery = db.query(Project.id).outerjoin(
        ProjectMember, Project.id == ProjectMember.project_id
    ).filter(
        or_(
            Project.owner_id == current_user.id,
            ProjectMember.user_id == current_user.id
        )
    )

    # 1. Project stats
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
            "overview": {
                "totalProjects": 0, "activeProjects": 0,
                "totalTasks": 0, "completedTasks": 0, "inProgressTasks": 0, "overdueTasks": 0,
                "teamMembers": 0, "completionRate": 0, "averageCompletionTime": 0, "teamVelocity": 0,
            },
            "trends": [], "projects": [], "team": [], "weeklyBurndown": []
        }

    active_projects = db.query(func.count(distinct(Project.id))).outerjoin(
        ProjectMember, Project.id == ProjectMember.project_id
    ).filter(
        or_(
            Project.owner_id == current_user.id,
            ProjectMember.user_id == current_user.id
        ),
        Project.is_active == True
    ).scalar() or 0

    # Task stats across all projects
    task_stats = db.query(
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
    # We join ProjectMember with our accessible projects subquery
    member_ids_count = db.query(func.count(distinct(ProjectMember.user_id))).filter(
        ProjectMember.project_id.in_(accessible_projects_subquery)
    ).scalar() or 0

    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Average completion time - DB Optimized
    # CTE for first completion time per task
    min_completion_dates = db.query(
        TaskHistory.task_id, 
        func.min(TaskHistory.timestamp).label('completed_at')
    ).filter(
        TaskHistory.project_id.in_(accessible_projects_subquery),
        TaskHistory.activity_type == ActivityType.TASK_COMPLETED
    ).group_by(TaskHistory.task_id).subquery()

    # Calculate average difference between created_at and completed_at
    avg_seconds = db.query(
        func.avg(extract('epoch', min_completion_dates.c.completed_at) - extract('epoch', Task.created_at))
    ).join(
        min_completion_dates, Task.id == min_completion_dates.c.task_id
    ).scalar()
    
    average_completion_time = (avg_seconds / 86400) if avg_seconds else 0

    # Project performance - Aggregated
    project_task_stats = db.query(
        Task.project_id,
        func.count(Task.id).label('total'),
        func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed')
    ).filter(
        Task.project_id.in_(accessible_projects_subquery)
    ).group_by(Task.project_id).subquery()
    
    # Get projects joined with stats
    projects_with_stats = db.query(
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
        
        # Velocity calculation based on progress
        velocity = "medium"
        if p_progress > 75:
            velocity = "high"
        elif p_progress < 25:
            velocity = "low"
            
        projects_data.append({  # type: ignore
            "name": p.name,
            "tasks": p_tasks,
            "completed": p_completed,
            "progress": round(p_progress, 1),
            "velocity": velocity
        })

    # Team performance - Aggregated
    # Get top 5 contributors
    team_stats = db.query(
        Task.assignee_id,
        func.count(Task.id).label('total'),
        func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label('completed')
    ).filter(
        Task.project_id.in_(accessible_projects_subquery),
        Task.assignee_id.isnot(None)
    ).group_by(Task.assignee_id).all()
    
    # Get user details for these contributors
    contributor_ids = [stat.assignee_id for stat in team_stats]
    users = db.query(User).filter(User.id.in_(contributor_ids)).all()
    user_map = {u.id: u for u in users}
    
    team_data = []
    for stat in team_stats:
        user = user_map.get(stat.assignee_id)
        if not user:
            continue
            
        m_tasks = stat.total
        m_completed = stat.completed
        m_efficiency = (m_completed / m_tasks * 100) if m_tasks > 0 else 0
        
        team_data.append({  # type: ignore
            "name": user.name,
            "avatar": user.avatar_url,
            "tasks": m_tasks,
            "completed": m_completed,
            "efficiency": round(m_efficiency, 1)
        })
    
    # Sort by efficiency and take top 5
    team_data.sort(key=lambda x: x['efficiency'], reverse=True)  # type: ignore
    team_data = team_data[:5]  # type: ignore

    # Weekly Burndown - Optimized Logic
    # 1. Period definition
    today = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    seven_days_ago = (today - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 2. Daily Created counts in range
    # Initial counts (cumulative up to start of period)
    initial_planned = db.query(func.count(Task.id)).filter(
        Task.project_id.in_(accessible_projects_subquery),
        Task.created_at < seven_days_ago
    ).scalar() or 0
    
    initial_actual = db.query(func.count(distinct(TaskHistory.task_id))).filter(
        TaskHistory.project_id.in_(accessible_projects_subquery),
        TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
        TaskHistory.timestamp < seven_days_ago
    ).scalar() or 0
    
    # Daily counts within period
    created_in_range = db.query(Task.created_at).filter(
        Task.project_id.in_(accessible_projects_subquery),
        Task.created_at >= seven_days_ago,
        Task.created_at <= today
    ).all()
    
    completed_in_range = db.query(TaskHistory.timestamp).filter(
        TaskHistory.project_id.in_(accessible_projects_subquery),
        TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
        TaskHistory.timestamp >= seven_days_ago,
        TaskHistory.timestamp <= today
    ).all()
    
    # Process into daily buckets
    weekly_burndown = []
    
    # Create simple map for O(1) lookups: date_str -> count
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
            
    # Build chart data
    current_planned = initial_planned
    current_actual = initial_actual
    
    for i in range(7):
        d = seven_days_ago + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        day_label = d.strftime("%a")
        
        # Add daily values to cumulative
        current_planned += created_map.get(d_str, 0)
        current_actual += completed_map.get(d_str, 0)
        
        weekly_burndown.append({
            "day": day_label,
            "planned": current_planned,
            "actual": current_actual
        })
    
    # Trends - Real Data
    # Calculate trends based on selected period (default 30d)
    days_map = {
        "7d": 7, "week": 7, 
        "30d": 30, "month": 30, 
        "90d": 90, "quarter": 90, 
        "1y": 365, "year": 365
    }
    days = days_map.get(period, 30)
    
    current_start = datetime.now() - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)
    
    # 1. Tasks Completed Trend
    current_completed_count = db.query(func.count(distinct(TaskHistory.task_id))).filter(
        TaskHistory.project_id.in_(accessible_projects_subquery),
        TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
        TaskHistory.timestamp >= current_start
    ).scalar() or 0
    
    previous_completed_count = db.query(func.count(distinct(TaskHistory.task_id))).filter(
        TaskHistory.project_id.in_(accessible_projects_subquery),
        TaskHistory.activity_type == ActivityType.TASK_COMPLETED,
        TaskHistory.timestamp >= previous_start,
        TaskHistory.timestamp < current_start
    ).scalar() or 0
    
    completed_change = current_completed_count - previous_completed_count
    div_base = previous_completed_count if previous_completed_count > 0 else 1
    completed_change_pct = (completed_change / div_base * 100)
    
    # 2. Project Velocity (Tasks/Day)
    current_velocity = current_completed_count / days
    previous_velocity = previous_completed_count / days
    velocity_change = current_velocity - previous_velocity
    div_base_vel = previous_velocity if previous_velocity > 0 else 1
    velocity_change_pct = (velocity_change / div_base_vel * 100)
    
    # 3. Team Productivity (Tasks/Member)
    active_members_count = member_ids_count or 1
    current_productivity = current_completed_count / active_members_count
    previous_productivity = previous_completed_count / active_members_count
    productivity_change = current_productivity - previous_productivity
    div_base_prod = previous_productivity if previous_productivity > 0 else 1
    productivity_change_pct = (productivity_change / div_base_prod * 100)
    
    trends = [  # type: ignore
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



@router.get("/projects/{project_id}/dashboard")
def get_dashboard_metrics(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    project_uuid: uuid.UUID = Depends(lambda: get_project_member(project_id, db, current_user))
) -> Dict[str, Any]:
    """
    Get dashboard metrics for a project.
    """
    
    
    # Get actual project metrics
    from models.task import Task, TaskStatus
    from models.project import ProjectMember
    
    # Task statistics
    total_tasks = db.query(Task).filter(Task.project_id == project_uuid).count()
    completed_tasks = db.query(Task).filter(
        Task.project_id == project_uuid,
        cast(Task.status, String) == TaskStatus.DONE.value
    ).count()
    todo_tasks = db.query(Task).filter(
        Task.project_id == project_uuid,
        cast(Task.status, String) == TaskStatus.TODO.value
    ).count()
    in_progress_tasks = db.query(Task).filter(
        Task.project_id == project_uuid,
        cast(Task.status, String) == TaskStatus.IN_PROGRESS.value
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
        
        formatted_activity = {  # type: ignore
            "id": str(activity.id),
            "type": activity.activity_type.value,
            "user_name": user_name,
            "task_title": activity.task_title,
            "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,  # type: ignore
            "description": activity.description
        }
        
        # Add additional context for specific activity types
        if activity.new_values:  # type: ignore
            try:
                new_values = json.loads(activity.new_values)  # type: ignore
                if "assignee_name" in new_values:
                    formatted_activity["assignee_name"] = new_values["assignee_name"]
            except (json.JSONDecodeError, TypeError):
                pass
        
        recent_activity.append(formatted_activity)  # type: ignore
    
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
    project_uuid: uuid.UUID = Depends(lambda: get_project_member(project_id, db, current_user))
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
        from models.task import Task, TaskStatus
        from datetime import datetime, timedelta, timezone
        # import random  # Not used
        
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
            
            day_tasks = [t for t in tasks if t.created_at and current_date <= t.created_at < next_date]  # type: ignore
            
            created_count = len(day_tasks)
            completed_count = len([t for t in day_tasks if cast(t.status, String) == TaskStatus.DONE.value])  # type: ignore
            
            productivity_data.append({  # type: ignore
                "date": current_date.isoformat(),
                "created_tasks": created_count,
                "completed_tasks": completed_count
            })
        
        logger.info(f"[DEBUG] Generated {len(productivity_data)} data points")  # type: ignore
        
        result = {  # type: ignore
            "period": period,
            "group_by": group_by,
            "data": productivity_data
        }
        
        logger.info(f"[DEBUG] Returning result with {len(productivity_data)} data points")  # type: ignore
        return result  # type: ignore
        
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
    current_user: User = Depends(get_current_active_user),
    project_uuid: uuid.UUID = Depends(lambda: get_project_member(project_id, db, current_user))
) -> Dict[str, Any]:
    """
    Get team contributions for a project.
    """
    
    
    from models.task import Task, TaskStatus
    from models.user import User
    from models.project import ProjectMember
    from sqlalchemy import func, distinct
    from sqlalchemy.orm import aliased
    
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
        (CompletedTask.project_id == project_uuid) & (CompletedTask.assignee_id == User.id) & (cast(CompletedTask.status, String) == TaskStatus.DONE.value)
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
        contributions.append({  # type: ignore
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
    current_user: User = Depends(get_current_active_user),
    project_uuid: uuid.UUID = Depends(lambda: get_project_member(project_id, db, current_user))
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
    
    # Get actual activity from database
    logger.info(f"[DEBUG] Calling task_history_service.get_recent_activities...")
    activities = task_history_service.get_recent_activities(project_uuid, limit)
    logger.info(f"[DEBUG] Retrieved {len(activities)} activities from database")
    
    # Get project information
    project = project_service.get_project_by_id(project_uuid)
    project_name = project.name if project else "Unknown Project"
    
    # Format activities for frontend
    formatted_activities = []
    for activity in activities:
        # Get user info
        user = db.query(User).filter(User.id == activity.user_id).first()
        user_name = user.name if user else f"User {activity.user_id}"
        
        formatted_activity = {  # type: ignore
            "id": str(activity.id),
            "type": activity.activity_type.value,
            "user_name": user_name,
            "task_title": activity.task_title,
            "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,  # type: ignore
            "description": activity.description,
            "project_name": project_name,
            "project_id": str(project_id)
        }
        
        # Add additional context for specific activity types
        if activity.new_values:  # type: ignore
            try:
                new_values = json.loads(activity.new_values)  # type: ignore
                if "assignee_name" in new_values:
                    formatted_activity["assignee_name"] = new_values["assignee_name"]
            except (json.JSONDecodeError, TypeError):
                pass
        
        formatted_activities.append(formatted_activity)  # type: ignore
        logger.debug(f"[DEBUG] Formatted activity: {formatted_activity}")
    
    logger.info(f"[DEBUG] Returning {len(formatted_activities)} formatted activities")  # type: ignore
    
    return {
        "activities": formatted_activities,
        "total_count": len(formatted_activities)  # type: ignore
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
    # from models.project import Project  # Not used
    
    logger.info(f"[DEBUG] get_all_recent_activity called:")
    logger.info(f"[DEBUG] - limit: {limit}")
    logger.info(f"[DEBUG] - current_user: {current_user.id} ({current_user.email})")
    
    project_service = ProjectService(db)
    task_history_service = TaskHistoryService(db)
    
    # Get all projects the user has access to (owner or member)
    user_projects = project_service.get_projects(user_id=uuid.UUID(str(current_user.id)))  # type: ignore
    project_ids = [p.id for p in user_projects]
    
    if not project_ids:
        return {
            "activities": [],
            "total_count": 0
        }
    
    logger.info(f"[DEBUG] User has access to {len(project_ids)} projects")
    
    # Get activities from all accessible projects
    try:
        activities = task_history_service.get_recent_activities_for_projects(project_ids, limit)
    except Exception as e:
        logger.error(f"[DEBUG] Error getting activities for projects: {e}")
        return {
            "activities": [],
            "total_count": 0
        }

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
    
    logger.info(f"[DEBUG] Returning {len(all_activities)} activities across all projects")
    
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
    from models.user import User
    # from models.project import Project  # Not used
    
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
    
    results: List[Dict[str, Any]] = []
    
    for project_id_str in project_ids:
        try:
            project_uuid = uuid.UUID(project_id_str)
        except ValueError:
            logger.error(f"[DEBUG] Invalid project ID format: {project_id_str}")
            results.append({  # type: ignore
                "projectId": project_id_str,
                "error": "Invalid project ID format"
            })
            continue
        
        try:
            # Check if user has access to this project
            project = project_service.get_project_by_id(project_uuid)
            if not project:
                logger.error(f"[DEBUG] Project not found: {project_uuid}")
                results.append({  # type: ignore
                    "projectId": project_id_str,
                    "error": "Project not found"
                })
                continue
            
            is_owner = project.owner_id == uuid.UUID(str(current_user.id))
            is_member = project_service.is_project_member(project_uuid, uuid.UUID(str(current_user.id)))  # type: ignore
            
            if not is_owner and not is_member:  # type: ignore
                logger.error(f"[DEBUG] User {current_user.id} has no access to project {project_uuid}")
                results.append({  # type: ignore
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
                
                formatted_activity = {  # type: ignore
                    "id": str(activity.id),
                    "type": activity.activity_type.value,
                    "user_name": user_name,
                    "task_title": activity.task_title,
                    "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,  # type: ignore
                    "description": activity.description
                }
                
                # Add additional context for specific activity types
                if activity.new_values:  # type: ignore
                    # import json  # Already imported at top level
                    try:
                        new_values = json.loads(activity.new_values)  # type: ignore
                        if "assignee_name" in new_values:
                            formatted_activity["assignee_name"] = new_values["assignee_name"]
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                formatted_activities.append(formatted_activity)  # type: ignore
            
            results.append({  # type: ignore
                "projectId": project_id_str,
                "activities": formatted_activities
            })
            
        except Exception as e:
            logger.error(f"[DEBUG] Error processing project {project_id_str}: {e}")
            results.append({  # type: ignore
                "projectId": project_id_str,
                "error": str(e)
            })
    
    logger.info(f"[DEBUG] Batch activity request completed for {len(results)} projects")  # type: ignore
    
    return results