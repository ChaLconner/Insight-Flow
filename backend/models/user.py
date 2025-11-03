"""
User model for the Insight-Flow application.
"""
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class User(BaseModel):
    """
    User model representing application users.
    """
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255))  # For password authentication
    avatar_url = Column(String(500))
    google_id = Column(String(255), unique=True, index=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    owned_projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    project_memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    assigned_tasks = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")
    created_tasks = relationship("Task", foreign_keys="Task.created_by", back_populates="creator")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")