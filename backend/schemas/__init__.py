"""
Pydantic schemas for Insight-Flow application.
"""
from .user import UserBase, UserCreate, UserUpdate, UserResponse, UserLogin, GoogleAuth
from .project import ProjectBase, ProjectCreate, ProjectUpdate, ProjectResponse, ProjectMemberBase, ProjectMemberCreate, ProjectMemberResponse, ProjectWithMembers
from .task import TaskBase, TaskCreate, TaskUpdate, TaskStatusUpdate, TaskAssign, TaskResponse, TaskWithDetails
from .notification import NotificationBase, NotificationCreate, NotificationResponse

__all__ = [
    "UserBase",
    "UserCreate", 
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "GoogleAuth",
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectMemberBase",
    "ProjectMemberCreate",
    "ProjectMemberResponse",
    "ProjectWithMembers",
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "TaskStatusUpdate",
    "TaskAssign",
    "TaskResponse",
    "TaskWithDetails",
    "NotificationBase",
    "NotificationCreate",
    "NotificationResponse",
]