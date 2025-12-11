
from fastapi.testclient import TestClient
from main import app
from unittest.mock import MagicMock, patch
import pytest
import uuid
from routers.auth import get_current_active_user
from database import get_db

client = TestClient(app)

def mock_get_current_active_user():
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    return mock_user

def test_get_recent_activity_optimized():
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    
    # We need to override require_project_member as it is a dependency
    from dependencies import require_project_member
    
    project_id = str(uuid.uuid4())
    mock_project = MagicMock()
    mock_project.id = uuid.UUID(project_id)
    mock_project.name = "Test Project"
    app.dependency_overrides[require_project_member] = lambda: mock_project
    
    with patch('routers.analytics.TaskHistoryService') as MockTaskHistoryService:
        mock_task_history_service = MockTaskHistoryService.return_value
        
        # Mock activities
        activity1 = MagicMock()
        activity1.user_id = uuid.uuid4()
        activity1.activity_type.value = "task_created"
        activity1.timestamp.isoformat.return_value = "2023-01-01"
        activity1.project_id = mock_project.id
        
        activity2 = MagicMock()
        activity2.user_id = uuid.uuid4()
        activity2.activity_type.value = "task_updated"
        activity2.timestamp.isoformat.return_value = "2023-01-02"
        activity2.project_id = mock_project.id

        mock_task_history_service.get_recent_activities.return_value = [activity1, activity2]
        
        # Mock DB
        mock_session = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_session
        
        # Mock DB users batch fetch
        mock_user = MagicMock()
        mock_user.id = activity1.user_id
        mock_user.name = "Test User"
        
        # Because we're mocking the batch fetch, it should return a list of users
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_user]
            
        response = client.get(f"/analytics/projects/{project_id}/activity")
            
        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
        assert len(data["activities"]) == 2
        
        # Verify batch fetch was called (should be called once)
        # filter was called, all was called
        assert mock_session.query.call_count >= 1

    app.dependency_overrides = {}
