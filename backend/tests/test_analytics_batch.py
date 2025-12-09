
from fastapi.testclient import TestClient
from main import app
from unittest.mock import MagicMock, patch
import pytest
import uuid
from routers.auth import get_current_active_user
from database import get_db

client = TestClient(app)

# Helper to override auth
def mock_get_current_active_user():
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    return mock_user

def test_get_batch_recent_activity():
    # Setup dependency overrides
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    
    with patch('routers.analytics.TaskHistoryService') as MockTaskHistoryService, \
         patch('routers.analytics.ProjectService') as MockProjectService:
         
        mock_project_service = MockProjectService.return_value
        mock_task_history_service = MockTaskHistoryService.return_value

        # Mock user projects
        project1 = MagicMock()
        project1.id = uuid.uuid4()
        project1.name = "Project 1"
        
        project2 = MagicMock()
        project2.id = uuid.uuid4()
        project2.name = "Project 2"

        mock_project_service.get_projects.return_value = [project1, project2]

        # Mock activities
        activity1 = MagicMock()
        activity1.project_id = project1.id
        activity1.user_id = uuid.uuid4() # Random user
        activity1.activity_type.value = "task_created"
        activity1.timestamp.isoformat.return_value = "2023-01-01"
        activity1.task_title = "Test Task"
        activity1.description = "Test Description"
        activity1.new_values = None
        
        # TaskHistoryService.get_recent_activities_for_projects return value
        mock_task_history_service.get_recent_activities_for_projects.return_value = [activity1]

        # Perform request
        # Note: we need to mock DB session inside the router or via dependency override to avoid errors if connection fails
        # But let's see if we can get away with just mocking the services if they are instantiated with db
        
        # We need to override get_db because the router iterates over results and queries DB for user details
        mock_session = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_session
        
        # Mock DB query for users
        mock_db_user = MagicMock()
        mock_db_user.id = activity1.user_id
        mock_db_user.name = "Test User"
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_db_user]

        response = client.post("/analytics/activity/batch", json={
            "project_ids": [str(project1.id), str(project2.id)],
            "limit": 5
        })
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    # Clean up
    app.dependency_overrides = {}


def test_get_batch_recent_activity_integration():
    from types import SimpleNamespace
    # Use real UUIDs
    p1_id = uuid.uuid4()
    p2_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    mock_user = MagicMock()
    mock_user.id = user_id
    
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    
    with patch('routers.analytics.TaskHistoryService') as MockTHS, \
         patch('routers.analytics.ProjectService') as MockPS:
         
        # Override get_db dependency
        mock_session = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_session
        
        # Mock Project Service
        ps_instance = MockPS.return_value
        # Use SimpleNamespace to avoid MagicMock attribute issues
        project1 = SimpleNamespace(id=p1_id, name="P1", owner_id=user_id)
        project2 = SimpleNamespace(id=p2_id, name="P2", owner_id=user_id)
        
        ps_instance.get_projects.return_value = [project1, project2]
        
        # Mock Task History Service
        ths_instance = MockTHS.return_value
        
        act1 = MagicMock()
        act1.id = uuid.uuid4()
        act1.project_id = p1_id
        act1.user_id = user_id
        act1.activity_type.value = "updated"
        act1.task_title = "Task 1"
        act1.description = "Desc"
        act1.timestamp.isoformat.return_value = "2023-01-01"
        act1.new_values = None
        
        ths_instance.get_recent_activities_for_projects.return_value = [act1]
        
        # Mock DB query for users
        mock_db_user = MagicMock()
        mock_db_user.id = user_id
        mock_db_user.name = "Test User"
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_db_user]

        response = client.post("/analytics/activity/batch", json={
            "project_ids": [str(p1_id), str(p2_id)],
            "limit": 10
        })
        
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        
        # Check result structure
        p1_res = next(r for r in results if r["projectId"] == str(p1_id))
        assert 'activities' in p1_res, f"Error in p1_res: {p1_res}"
        assert len(p1_res["activities"]) == 1
        assert p1_res["activities"][0]["task_title"] == "Task 1"
        
    app.dependency_overrides = {}

