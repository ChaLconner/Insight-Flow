"""
Analytics model for storing pre-computed analytics data.
"""
from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, Float, Integer, Text, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum
from datetime import datetime

class AnalyticsPeriod(enum.Enum):
    """Enum for analytics periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class ProjectAnalytics(BaseModel):
    """
    ProjectAnalytics model for storing pre-computed project analytics.
    """
    __tablename__ = "project_analytics"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    period = Column(String(10), nullable=False, index=True)  # daily, weekly, monthly
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Task statistics
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    todo_tasks = Column(Integer, default=0)
    in_progress_tasks = Column(Integer, default=0)
    
    # Productivity metrics
    productivity_score = Column(Float, default=0.0)
    completion_rate = Column(Float, default=0.0)
    average_completion_time = Column(Float)  # in hours
    
    # Member activity
    active_members = Column(Integer, default=0)
    total_activities = Column(Integer, default=0)
    
    # Additional metrics stored as JSON
    metrics_data = Column(JSON)
    
    # Relationships
    project = relationship("Project", back_populates="analytics")

class UserProductivity(BaseModel):
    """
    UserProductivity model for tracking user productivity over time.
    """
    __tablename__ = "user_productivity"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    period = Column(String(10), nullable=False, index=True)  # daily, weekly, monthly
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Task statistics
    tasks_created = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    tasks_assigned = Column(Integer, default=0)
    
    # Time tracking
    total_time_spent = Column(Float)  # in hours
    average_completion_time = Column(Float)  # in hours
    
    # Productivity score
    productivity_score = Column(Float, default=0.0)
    
    # Relationships
    user = relationship("User", back_populates="productivity")
    project = relationship("Project", back_populates="user_productivity")

class TaskTimeTracking(BaseModel):
    """
    TaskTimeTracking model for tracking time spent on tasks.
    """
    __tablename__ = "task_time_tracking"
    
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Time tracking
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)  # total time spent in minutes
    
    # Status tracking
    is_active = Column(String(20), default="active")  # active, paused, completed
    
    # Notes
    notes = Column(Text)
    
    # Relationships
    task = relationship("Task", back_populates="time_tracking")
    user = relationship("User", back_populates="time_tracking")

class ProjectMilestone(BaseModel):
    """
    ProjectMilestone model for tracking project milestones.
    """
    __tablename__ = "project_milestones"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Dates
    due_date = Column(DateTime(timezone=True), index=True)
    completed_at = Column(DateTime(timezone=True))
    
    # Status
    is_completed = Column(String(20), default="pending")  # pending, completed, cancelled
    progress_percentage = Column(Integer, default=0)
    
    # Relationships
    project = relationship("Project", back_populates="milestones")

class TaskDependency(BaseModel):
    """
    TaskDependency model for managing task dependencies.
    """
    __tablename__ = "task_dependencies"
    
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    depends_on_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    dependency_type = Column(String(20), default="finish_to_start")  # finish_to_start, start_to_start
    
    # Relationships
    task = relationship("Task", foreign_keys="TaskDependency.task_id", back_populates="dependencies")
    depends_on_task = relationship("Task", foreign_keys="TaskDependency.depends_on_task_id", back_populates="dependents")

class TaskComment(BaseModel):
    """
    TaskComment model for task comments and discussions.
    """
    __tablename__ = "task_comments"
    
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    
    # Comment metadata
    is_edited = Column(String(10), default="false")
    edited_at = Column(DateTime(timezone=True))
    
    # Relationships
    task = relationship("Task", back_populates="comments")
    user = relationship("User", back_populates="task_comments")

class TaskAttachment(BaseModel):
    """
    TaskAttachment model for file attachments to tasks.
    """
    __tablename__ = "task_attachments"
    
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # File information
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(100))
    
    # Relationships
    task = relationship("Task", back_populates="attachments")
    uploaded_by_user = relationship("User", back_populates="uploaded_attachments")

class ProjectTag(BaseModel):
    """
    ProjectTag model for categorizing projects.
    """
    __tablename__ = "project_tags"
    
    name = Column(String(100), nullable=False, unique=True, index=True)
    color = Column(String(7))  # hex color code
    description = Column(Text)
    
    # Relationships
    project_associations = relationship("ProjectTagAssociation", back_populates="tag")

class ProjectTagAssociation(BaseModel):
    """
    ProjectTagAssociation model for many-to-many relationship between projects and tags.
    """
    __tablename__ = "project_tag_associations"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("project_tags.id"), nullable=False, index=True)
    
    # Relationships
    project = relationship("Project", back_populates="tag_associations")
    tag = relationship("ProjectTag", back_populates="project_associations")