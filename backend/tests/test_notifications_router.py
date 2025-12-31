
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from main import app
from dependencies.services import get_async_notification_service
from routers.auth import get_current_active_user
from models.user import User

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_notification_service():
    service = AsyncMock()
    return service

@pytest.fixture
def mock_current_user():
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.raw_password = None
    return user

@pytest.fixture
def client(mock_notification_service, mock_current_user):
    app.dependency_overrides[get_async_notification_service] = lambda: mock_notification_service
    app.dependency_overrides[get_current_active_user] = lambda: mock_current_user
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides = {}

# ============================================================================
# Tests
# ============================================================================

def test_get_notifications(client, mock_notification_service):
    notif = MagicMock()
    notif.id = uuid4()
    notif.user_id = uuid4()
    notif.type = "info"
    notif.title = "Test"
    notif.message = "Message"
    notif.data = {}
    notif.is_read = False
    notif.created_at = datetime.now()
    
    mock_notification_service.get_user_notifications.return_value = [notif]
    
    response = client.get("/api/v1/notifications/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test"

def test_get_unread_count(client, mock_notification_service):
    mock_notification_service.get_unread_count.return_value = 5
    response = client.get("/api/v1/notifications/unread-count")
    assert response.status_code == 200
    assert response.json() == 5

def test_mark_notification_read(client, mock_notification_service):
    notif_id = str(uuid4())
    
    notif = MagicMock()
    notif.id = notif_id
    notif.user_id = uuid4()
    notif.type = "info"
    notif.title = "Read Test"
    notif.message = "Message" # Ensure valid string
    notif.data = {}
    notif.is_read = True
    notif.created_at = datetime.now()
    
    mock_notification_service.mark_notification_read.return_value = notif
    
    response = client.put(f"/api/v1/notifications/{notif_id}/read")
    assert response.status_code == 200
    assert response.json()["read"] is True

def test_mark_notification_read_invalid_id(client):
    response = client.put("/api/v1/notifications/invalid-uuid/read")
    assert response.status_code == 400

def test_mark_notification_read_not_found(client, mock_notification_service):
    mock_notification_service.mark_notification_read.side_effect = ValueError("Not found")
    notif_id = str(uuid4())
    response = client.put(f"/api/v1/notifications/{notif_id}/read")
    assert response.status_code == 404

def test_mark_all_read(client, mock_notification_service):
    mock_notification_service.mark_all_notifications_read.return_value = 10
    response = client.put("/api/v1/notifications/read-all")
    assert response.status_code == 200
    assert response.json()["count"] == 10

def test_delete_notification(client, mock_notification_service):
    notif_id = str(uuid4())
    mock_notification_service.delete_notification.return_value = True
    
    response = client.delete(f"/api/v1/notifications/{notif_id}")
    assert response.status_code == 204

def test_delete_notification_not_found(client, mock_notification_service):
    mock_notification_service.delete_notification.side_effect = ValueError("Not found")
    notif_id = str(uuid4())
    response = client.delete(f"/api/v1/notifications/{notif_id}")
    assert response.status_code == 404

def test_check_deadlines(client):
    with patch("routers.notifications.run_async_deadline_check", new_callable=AsyncMock) as mock_run:
         mock_run.return_value = {"processed": 5}
         response = client.post("/api/v1/notifications/check-deadlines")
         assert response.status_code == 200
         assert response.json()["summary"]["processed"] == 5

def test_create_test_notifications(client, mock_notification_service):
    response = client.post("/api/v1/notifications/create-test")
    assert response.status_code == 200
    assert mock_notification_service.create_notification.call_count == 3
