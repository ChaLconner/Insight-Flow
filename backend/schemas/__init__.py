"""
Pydantic schemas for Insight-Flow application.
"""

from .dashboard import (
    ActivityProjectResponse,
    ActivityUserResponse,
    DashboardActivityResponse,
    DashboardOverviewResponse,
    DashboardProjectResponse,
    DashboardStatsResponse,
    TodayTaskResponse,
)
from .notification import NotificationCreate, NotificationResponse
from .password_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from .project import ProjectCreate, ProjectMemberResponse, ProjectResponse, ProjectUpdate
from .task import TaskCreate, TaskResponse, TaskUpdate
from .user import GoogleAuth, Token, UserCreate, UserLogin, UserResponse

__all__ = [
    "ActivityProjectResponse",
    "ActivityUserResponse",
    "DashboardActivityResponse",
    "DashboardOverviewResponse",
    "DashboardProjectResponse",
    "DashboardStatsResponse",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "GoogleAuth",
    "NotificationCreate",
    "NotificationResponse",
    "ProjectCreate",
    "ProjectMemberResponse",
    "ProjectResponse",
    "ProjectUpdate",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
    "TaskCreate",
    "TaskResponse",
    "TaskUpdate",
    "TodayTaskResponse",
    "Token",
    "UserCreate",
    "UserLogin",
    "UserResponse",
]
