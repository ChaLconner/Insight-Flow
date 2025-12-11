"""
User model for Insight-Flow application.
"""
from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship
from .base import BaseModel

class User(BaseModel):
    """
    User model representing application users.
    """
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)  # Made nullable to support first_name/last_name
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    username = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255))  # For password authentication
    avatar_url = Column(String(500))
    google_id = Column(String(255), unique=True, index=True)
    is_active = Column(Boolean, default=True)
    # role field is optional to support existing databases without the field
    # will be set to default value "user" if not present
    role = Column(String(50), nullable=True)
    
    # Extended profile fields
    phone = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Relationships
    owned_projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    project_memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    assigned_tasks = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")
    created_tasks = relationship("Task", foreign_keys="Task.created_by", back_populates="creator")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    productivity = relationship("UserProductivity", back_populates="user", cascade="all, delete-orphan")
    time_tracking = relationship("TaskTimeTracking", back_populates="user", cascade="all, delete-orphan")
    task_comments = relationship("TaskComment", back_populates="user", cascade="all, delete-orphan")
    uploaded_attachments = relationship("TaskAttachment", back_populates="uploaded_by_user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")