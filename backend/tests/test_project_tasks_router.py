"""
Tests for routers/project_tasks.py helper functions.
"""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

from models.task import TaskPriority, TaskStatus

# ============================================================================
# Helper Functions
# ============================================================================


def create_mock_task(project_id, task_id=None):
    """Helper to create a mock task with all required attributes."""
    task = MagicMock()
    task.id = task_id or uuid4()
    task.title = "Test Task"
    task.description = "Test Description"
    task.status = TaskStatus.TODO
    task.priority = TaskPriority.MEDIUM
    task.type = "feature"
    task.project_id = project_id
    task.assignee_id = None
    task.created_by = uuid4()
    task.due_date = None
    task.created_at = datetime.now()
    task.updated_at = datetime.now()
    task.assignee = None
    task.creator = None
    task.project = None
    return task


# ============================================================================
# Tests for helper functions
# ============================================================================


class TestProjectTasksHelpers:
    def test_get_status_value_from_enum(self):
        """Test extracting status value from enum."""
        from routers.project_tasks import _get_status_value

        result = _get_status_value(TaskStatus.TODO)
        assert result == "todo"

        result = _get_status_value(TaskStatus.IN_PROGRESS)
        assert result == "in_progress"

    def test_get_status_value_from_string(self):
        """Test extracting status value from string."""
        from routers.project_tasks import _get_status_value

        result = _get_status_value("DONE")
        assert result == "done"

        # Edge case: empty string returns 'todo'
        result = _get_status_value("")
        assert result == "todo"

    def test_build_task_response(self):
        """Test building task response dict."""
        from routers.project_tasks import _build_task_response

        project_id = uuid4()
        task = create_mock_task(project_id)

        result = _build_task_response(task)

        assert result["id"] == task.id
        assert result["title"] == "Test Task"
        assert result["status"] == "todo"
        assert result["project_id"] == project_id

    def test_build_task_with_details_response(self):
        """Test building task with details response dict."""
        from routers.project_tasks import _build_task_with_details_response

        project_id = uuid4()
        task = create_mock_task(project_id)

        result = _build_task_with_details_response(task)

        assert "assignee" in result
        assert "creator" in result
        assert "project" in result
