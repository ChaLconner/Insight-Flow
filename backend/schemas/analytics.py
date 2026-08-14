from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ActivityType(StrEnum):
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
    task_title: str | None = None
    timestamp: str | None = None  # ISO format string
    description: str | None = None
    project_name: str
    project_id: str
    assignee_name: str | None = None


class BatchActivityRequest(BaseModel):
    project_ids: list[str] = Field(..., max_length=20, description="Max 20 projects per batch")
    limit: int = Field(default=10, ge=1, le=50, description="Activities per project (max 50)")


class BatchActivityResponse(BaseModel):
    projectId: str
    activities: list[ActivityResponse] | None = None
    error: str | None = None


class AnalyticsTrend(BaseModel):
    metric: str
    current: float
    previous: float
    change: float
    trend: str  # "up" | "down"


class ProjectMetricResponse(BaseModel):
    id: str
    name: str
    tasks: int
    completed: int
    progress: float
    velocity: str  # "high" | "medium" | "low"


class TeamMemberMetricResponse(BaseModel):
    id: str | None = None
    name: str
    avatar: str | None = None
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
    avatar: str | None = None
    tasks: int


class TeamWorkloadPaginatedResponse(BaseModel):
    """Paginated team workload response for handling large user counts"""

    items: list[TeamWorkload] = Field(default_factory=list)
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
    weeklyBurndown: list[BurndownDataPoint] = Field(default_factory=list)
    trends: list[AnalyticsTrend] = Field(default_factory=list)
    projects: list[ProjectMetricResponse] = Field(default_factory=list)
    team: list[TeamMemberMetricResponse] = Field(default_factory=list)
    statusDistribution: list[StatusDistribution] = Field(default_factory=list)
    priorityDistribution: list[PriorityDistribution] = Field(default_factory=list)
    teamWorkload: list[TeamWorkload] = Field(default_factory=list)
    teamWorkloadTotal: int = Field(default=0, ge=0)
    dailyTrends: list[DailyTrend] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
