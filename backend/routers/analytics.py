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
    
    # For now, return empty metrics
    return {
        "total_tasks": 0,
        "completed_tasks": 0,
        "total_members": 0,
        "productivity_score": 0.0
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
    
    # For now, return empty productivity data
    return {
        "period": period,
        "group_by": group_by,
        "data": []
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
    
    # For now, return empty contributions data
    return {
        "project_id": project_uuid,
        "contributions": []
    }