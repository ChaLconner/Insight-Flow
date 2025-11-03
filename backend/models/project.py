"""
Project models for Insight-Flow application.
"""
from sqlalchemy import Column, String, Boolean, UUID, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

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
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")