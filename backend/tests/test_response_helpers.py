"""
Tests for utils/response_helpers.py
"""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime

from utils.response_helpers import (
    build_member_summary,
    build_member_summaries,
    build_user_response,
    build_project_member_response,
    build_project_member_responses,
    build_project_response,
    build_project_with_members_response,
    build_task_response,
    build_notification_response,
)


class TestBuildMemberSummary:
    def test_build_member_summary_with_user(self):
        """Test building member summary with user data."""
        member = MagicMock()
        member.id = uuid4()
        member.user_id = uuid4()
        member.role = "owner"
        member.user = MagicMock()
        member.user.name = "Test User"
        member.user.email = "test@example.com"
        member.user.avatar_url = "https://example.com/avatar.png"
        
        result = build_member_summary(member)
        
        assert result["id"] == str(member.id)
        assert result["user_id"] == str(member.user_id)
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"
        assert result["role"] == "owner"

    def test_build_member_summary_without_user(self):
        """Test building member summary when user is None."""
        member = MagicMock()
        member.id = uuid4()
        member.user_id = uuid4()
        member.role = "member"
        member.user = None
        
        result = build_member_summary(member)
        
        assert result["name"] == "Unknown"
        assert result["email"] == ""


class TestBuildMemberSummaries:
    def test_build_member_summaries(self):
        """Test building multiple member summaries."""
        member1 = MagicMock()
        member1.id = uuid4()
        member1.user_id = uuid4()
        member1.role = "owner"
        member1.user = MagicMock()
        member1.user.name = "User 1"
        member1.user.email = "user1@example.com"
        member1.user.avatar_url = None
        
        member2 = MagicMock()
        member2.id = uuid4()
        member2.user_id = uuid4()
        member2.role = "member"
        member2.user = MagicMock()
        member2.user.name = "User 2"
        member2.user.email = "user2@example.com"
        member2.user.avatar_url = None
        
        result = build_member_summaries([member1, member2])
        
        assert len(result) == 2
        assert result[0]["name"] == "User 1"
        assert result[1]["name"] == "User 2"


class TestBuildUserResponse:
    def test_build_user_response(self):
        """Test building user response."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "test@example.com"
        user.name = "Test User"
        user.avatar_url = "https://example.com/avatar.png"
        user.is_active = True
        user.role = "admin"
        user.created_at = datetime.now()
        user.updated_at = datetime.now()
        
        result = build_user_response(user)
        
        assert result["id"] == user.id
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert result["is_active"] is True
        assert result["role"] == "admin"

    def test_build_user_response_no_role(self):
        """Test building user response with no role."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "test@example.com"
        user.name = "Test User"
        user.avatar_url = None
        user.is_active = True
        user.role = None
        user.created_at = datetime.now()
        user.updated_at = datetime.now()
        
        result = build_user_response(user)
        
        assert result["role"] == "user"  # Default


class TestBuildProjectMemberResponse:
    def test_build_project_member_response(self):
        """Test building project member response."""
        member = MagicMock()
        member.id = uuid4()
        member.project_id = uuid4()
        member.user_id = uuid4()
        member.role = "owner"
        member.joined_at = datetime.now()
        member.user = MagicMock()
        member.user.id = member.user_id
        member.user.email = "test@example.com"
        member.user.name = "Test User"
        member.user.avatar_url = None
        member.user.is_active = True
        member.user.role = "user"
        member.user.created_at = datetime.now()
        member.user.updated_at = datetime.now()
        
        result = build_project_member_response(member)
        
        assert result["id"] == member.id
        assert result["project_id"] == member.project_id
        assert result["role"] == "owner"
        assert result["user"] is not None

    def test_build_project_member_response_no_user(self):
        """Test building project member response without user."""
        member = MagicMock()
        member.id = uuid4()
        member.project_id = uuid4()
        member.user_id = uuid4()
        member.role = "member"
        member.joined_at = datetime.now()
        member.user = None
        
        result = build_project_member_response(member)
        
        assert result["user"] is None


class TestBuildProjectResponse:
    def test_build_project_response_with_details(self):
        """Test building project response with details."""
        project = MagicMock()
        project.id = uuid4()
        project.name = "Test Project"
        project.description = "Description"
        project.owner_id = uuid4()
        project.is_active = True
        project.created_at = datetime.now()
        project.updated_at = datetime.now()
        
        details = {
            "task_count": 10,
            "completed_tasks": 5,
            "overdue_tasks": 2,
            "recent_activity": None,
            "member_count": 3
        }
        
        result = build_project_response(project, details)
        
        assert result["name"] == "Test Project"
        assert result["task_count"] == 10
        assert result["completed_tasks"] == 5
        assert result["member_count"] == 3

    def test_build_project_response_without_details(self):
        """Test building project response without details."""
        project = MagicMock()
        project.id = uuid4()
        project.name = "Test Project"
        project.description = "Description"
        project.owner_id = uuid4()
        project.is_active = True
        project.created_at = datetime.now()
        project.updated_at = datetime.now()
        
        result = build_project_response(project)
        
        assert result["task_count"] == 0
        assert result["completed_tasks"] == 0
        assert result["member_count"] == 0

    def test_build_project_response_with_members(self):
        """Test building project response with member summaries."""
        project = MagicMock()
        project.id = uuid4()
        project.name = "Test Project"
        project.description = None
        project.owner_id = uuid4()
        project.is_active = True
        project.created_at = datetime.now()
        project.updated_at = datetime.now()
        
        member = MagicMock()
        member.id = uuid4()
        member.user_id = uuid4()
        member.role = "owner"
        member.user = MagicMock()
        member.user.name = "Owner"
        member.user.email = "owner@example.com"
        member.user.avatar_url = None
        
        result = build_project_response(project, members=[member])
        
        assert "member_summaries" in result
        assert len(result["member_summaries"]) == 1


class TestBuildTaskResponse:
    def test_build_task_response_basic(self):
        """Test building task response."""
        task = MagicMock()
        task.id = uuid4()
        task.title = "Test Task"
        task.description = "Description"
        task.status = MagicMock()
        task.status.value = "todo"
        task.priority = MagicMock()
        task.priority.value = "medium"
        task.project_id = uuid4()
        task.assignee_id = None
        task.creator_id = uuid4()
        task.due_date = None
        task.created_at = datetime.now()
        task.updated_at = datetime.now()
        
        result = build_task_response(task, include_relations=False)
        
        assert result["title"] == "Test Task"
        assert result["status"] == "todo"
        assert result["priority"] == "medium"

    def test_build_task_response_with_relations(self):
        """Test building task response with relations."""
        task = MagicMock()
        task.id = uuid4()
        task.title = "Test Task"
        task.description = "Description"
        task.status = "done"
        task.priority = "high"
        task.project_id = uuid4()
        task.assignee_id = uuid4()
        task.creator_id = uuid4()
        task.due_date = None
        task.created_at = datetime.now()
        task.updated_at = datetime.now()
        
        task.assignee = MagicMock()
        task.assignee.id = task.assignee_id
        task.assignee.email = "assignee@example.com"
        task.assignee.name = "Assignee"
        task.assignee.avatar_url = None
        task.assignee.is_active = True
        task.assignee.role = "user"
        task.assignee.created_at = datetime.now()
        task.assignee.updated_at = datetime.now()
        
        task.creator = MagicMock()
        task.creator.id = task.creator_id
        task.creator.email = "creator@example.com"
        task.creator.name = "Creator"
        task.creator.avatar_url = None
        task.creator.is_active = True
        task.creator.role = "user"
        task.creator.created_at = datetime.now()
        task.creator.updated_at = datetime.now()
        
        task.project = MagicMock()
        task.project.name = "Project"
        
        result = build_task_response(task, include_relations=True)
        
        assert result["title"] == "Test Task"
        assert "assignee" in result
        assert "creator" in result
        assert result["project_name"] == "Project"


class TestBuildNotificationResponse:
    def test_build_notification_response(self):
        """Test building notification response."""
        notification = MagicMock()
        notification.id = uuid4()
        notification.user_id = uuid4()
        notification.type = "task_assigned"
        notification.title = "New Task"
        notification.message = "You have been assigned a task"
        notification.data = {"task_id": str(uuid4())}
        notification.is_read = False
        notification.created_at = datetime.now()
        
        result = build_notification_response(notification)
        
        assert result["type"] == "task_assigned"
        assert result["title"] == "New Task"
        assert result["is_read"] is False
