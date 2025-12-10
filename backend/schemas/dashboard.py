"""
Dashboard Pydantic schemas for type-safe API responses.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response model."""
    totalProjects: int = Field(default=0, description="Total number of projects")
    totalProjectsChange: str = Field(default="+0%", description="Change percentage from last period")
    totalProjectsTrend: Literal["up", "down"] = Field(default="up", description="Trend direction")
    
    totalTasks: int = Field(default=0, description="Total number of tasks")
    completedTasks: int = Field(default=0, description="Number of completed tasks")
    
    inProgressTasks: int = Field(default=0, description="Number of in-progress tasks")
    inProgressTasksChange: str = Field(default="+0%", description="Change percentage")
    inProgressTasksTrend: Literal["up", "down"] = Field(default="up", description="Trend direction")
    
    pendingReviewTasks: int = Field(default=0, description="Number of tasks pending review")
    pendingReviewTasksChange: str = Field(default="+0%", description="Change percentage")
    pendingReviewTasksTrend: Literal["up", "down"] = Field(default="up", description="Trend direction")
    
    teamVelocity: int = Field(default=0, description="Team velocity metric")
    teamVelocityChange: str = Field(default="+0%", description="Change percentage")
    teamVelocityTrend: Literal["up", "down"] = Field(default="up", description="Trend direction")

    class Config:
        json_schema_extra = {
            "example": {
                "totalProjects": 5,
                "totalProjectsChange": "+20%",
                "totalProjectsTrend": "up",
                "totalTasks": 50,
                "completedTasks": 30,
                "inProgressTasks": 15,
                "inProgressTasksChange": "+10%",
                "inProgressTasksTrend": "up",
                "pendingReviewTasks": 5,
                "pendingReviewTasksChange": "-5%",
                "pendingReviewTasksTrend": "down",
                "teamVelocity": 12,
                "teamVelocityChange": "+8%",
                "teamVelocityTrend": "up"
            }
        }


class DashboardProjectResponse(BaseModel):
    """Project item in dashboard response."""
    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(default=None, description="Project description")
    progress: int = Field(default=0, ge=0, le=100, description="Project progress percentage")
    color: str = Field(default="#6366f1", description="Project color hex code")
    updated_at: Optional[str] = Field(default=None, description="Last updated timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Project Alpha",
                "description": "Main development project",
                "progress": 75,
                "color": "#6366f1",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class ActivityUserResponse(BaseModel):
    """User info in activity response."""
    id: str = Field(..., description="User ID")
    name: str = Field(..., description="User name")
    avatar: Optional[str] = Field(default=None, description="User avatar URL")


class ActivityProjectResponse(BaseModel):
    """Project info in activity response."""
    id: Optional[str] = Field(default=None, description="Project ID")
    name: str = Field(..., description="Project name")


class DashboardActivityResponse(BaseModel):
    """Activity item in dashboard response."""
    id: str = Field(..., description="Activity ID")
    user: ActivityUserResponse = Field(..., description="User who performed the action")
    action: str = Field(..., description="Action description")
    target: Optional[str] = Field(default=None, description="Target of the action")
    time: Optional[str] = Field(default=None, description="Activity timestamp")
    project: Optional[ActivityProjectResponse] = Field(default=None, description="Related project")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "act-123",
                "user": {
                    "id": "user-456",
                    "name": "John Doe",
                    "avatar": "/avatars/john.jpg"
                },
                "action": "completed task",
                "target": "Implement login feature",
                "time": "2024-01-15T10:30:00Z",
                "project": {
                    "id": "proj-789",
                    "name": "Project Alpha"
                }
            }
        }


class DashboardOverviewResponse(BaseModel):
    """Complete dashboard overview response."""
    stats: DashboardStatsResponse = Field(..., description="Dashboard statistics")
    recentProjects: List[DashboardProjectResponse] = Field(
        default_factory=list, 
        description="List of recent projects"
    )
    recentActivities: List[DashboardActivityResponse] = Field(
        default_factory=list, 
        description="List of recent activities"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "stats": {
                    "totalProjects": 5,
                    "totalProjectsChange": "+20%",
                    "totalProjectsTrend": "up",
                    "totalTasks": 50,
                    "completedTasks": 30,
                    "inProgressTasks": 15,
                    "inProgressTasksChange": "+10%",
                    "inProgressTasksTrend": "up",
                    "pendingReviewTasks": 5,
                    "pendingReviewTasksChange": "-5%",
                    "pendingReviewTasksTrend": "down",
                    "teamVelocity": 12,
                    "teamVelocityChange": "+8%",
                    "teamVelocityTrend": "up"
                },
                "recentProjects": [],
                "recentActivities": []
            }
        }


class TodayTaskResponse(BaseModel):
    """Task for today's tasks endpoint."""
    id: str = Field(..., description="Task ID")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(default=None, description="Task description")
    status: str = Field(..., description="Task status")
    priority: str = Field(default="medium", description="Task priority")
    due_date: Optional[str] = Field(default=None, description="Due date")
    project: Optional[DashboardProjectResponse] = Field(default=None, description="Related project")
