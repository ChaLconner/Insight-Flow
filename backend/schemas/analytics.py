from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum

class ActivityType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_DELETED = "task_deleted"
    COMMENT_ADDED = "comment_added"
    # Add other types as needed based on ActivityType enum in models

class ActivityResponse(BaseModel):
    id: str
    type: str  # using str to be safe if enum values vary, or use ActivityType
    user_name: str
    task_title: Optional[str] = None
    timestamp: Optional[str] = None # ISO format string
    description: Optional[str] = None
    project_name: str
    project_id: str
    assignee_name: Optional[str] = None

class BatchActivityRequest(BaseModel):
    project_ids: List[str]
    limit: Optional[int] = 10

class BatchActivityResponse(BaseModel):
    projectId: str
    activities: Optional[List[ActivityResponse]] = None
    error: Optional[str] = None

class AnalyticsTrend(BaseModel):
    metric: str
    current: float
    previous: float
    change: float
    trend: str # "up" | "down"

class ProjectMetricResponse(BaseModel):
    id: str
    name: str
    tasks: int
    completed: int
    progress: float
    velocity: str # "high" | "medium" | "low"

class TeamMemberMetricResponse(BaseModel):
    name: str
    avatar: Optional[str] = None
    tasks: int
    completed: int
    efficiency: float

class BurndownDataPoint(BaseModel):
    day: str
    planned: int
    actual: int

# New schemas for complete analytics response
class StatusDistribution(BaseModel):
    """Task status distribution data point"""
    name: str
    value: int

class PriorityDistribution(BaseModel):
    """Task priority distribution data point"""
    name: str
    value: int

class TeamWorkload(BaseModel):
    """Team member workload data"""
    name: str
    avatar: Optional[str] = None
    tasks: int

class TeamWorkloadPaginatedResponse(BaseModel):
    """Paginated team workload response for handling large user counts"""
    items: List[TeamWorkload] = []
    total: int = Field(default=0, ge=0, description="Total number of team members")
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Number of items per page")
    total_pages: int = Field(default=0, ge=0, description="Total number of pages")
    has_next: bool = Field(default=False, description="Whether there are more pages")
    has_prev: bool = Field(default=False, description="Whether there are previous pages")

    model_config = ConfigDict(from_attributes=True)

class DailyTrend(BaseModel):
    """Daily task creation/completion trend"""
    date: str
    created: int
    completed: int

class AnalyticsOverviewMetrics(BaseModel):
    """Core analytics overview metrics"""
    totalProjects: int = Field(default=0, ge=0)
    activeProjects: int = Field(default=0, ge=0)
    totalTasks: int = Field(default=0, ge=0)
    completedTasks: int = Field(default=0, ge=0)
    inProgressTasks: int = Field(default=0, ge=0)
    overdueTasks: int = Field(default=0, ge=0)
    teamMembers: int = Field(default=0, ge=0)
    completionRate: float = Field(default=0.0, ge=0.0, le=100.0)
    averageCompletionTime: float = Field(default=0.0, ge=0.0)
    teamVelocity: float = Field(default=0.0, ge=0.0)

class AnalyticsOverviewResponse(BaseModel):
    """Complete analytics overview response"""
    overview: AnalyticsOverviewMetrics
    weeklyBurndown: List[BurndownDataPoint] = []
    trends: List[AnalyticsTrend] = []
    projects: List[ProjectMetricResponse] = []
    team: List[TeamMemberMetricResponse] = []
    statusDistribution: List[StatusDistribution] = []
    priorityDistribution: List[PriorityDistribution] = []
    teamWorkload: List[TeamWorkload] = []
    dailyTrends: List[DailyTrend] = []
    
    model_config = ConfigDict(from_attributes=True)
