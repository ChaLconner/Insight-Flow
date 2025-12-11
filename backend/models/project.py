"""
Project models for Insight-Flow application.
"""
from sqlalchemy import Column, String, Boolean, UUID, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel
import enum
from datetime import datetime, timezone

class Project(BaseModel):
    """
    Project model representing team projects.
    """
    __tablename__ = "projects"
    
    name = Column(String(255), nullable=False)
    description = Column(String)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    owner = relationship("User", back_populates="owned_projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    analytics = relationship("ProjectAnalytics", back_populates="project", cascade="all, delete-orphan")
    user_productivity = relationship("UserProductivity", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("ProjectMilestone", back_populates="project", cascade="all, delete-orphan")
    tag_associations = relationship("ProjectTagAssociation", back_populates="project", cascade="all, delete-orphan")

class MemberRole(enum.Enum):
    """Enum for project member roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

class ProjectMember(BaseModel):
    """
    ProjectMember model representing many-to-many relationship between users and projects.
    """
    __tablename__ = "project_members"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, default=MemberRole.MEMBER.value)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")

    from sqlalchemy import Index
    __table_args__ = (
        Index('ix_project_members_project_user', 'project_id', 'user_id'),
    )