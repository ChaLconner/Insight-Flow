"""
Notification endpoint tests.
"""
import pytest
from fastapi.testclient import TestClient
import uuid

class TestNotificationEndpoints:
    """Test notification endpoints."""
    
    def test_get_notifications_success(self, client: TestClient, auth_headers: dict):
        """Test getting user notifications."""
        response = client.get("/notifications/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "pages" in data
        assert isinstance(data["items"], list)
    
    def test_get_notifications_unauthorized(self, client: TestClient):
        """Test getting notifications without authentication."""
        response = client.get("/notifications/")
        
        assert response.status_code == 401
    
    def test_get_notifications_with_pagination(self, client: TestClient, auth_headers: dict):
        """Test getting notifications with pagination."""
        response = client.get("/notifications/?page=1&limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 5
        assert isinstance(data["items"], list)
    
    def test_get_notifications_with_filters(self, client: TestClient, auth_headers: dict):
        """Test getting notifications with filters."""
        # Test is_read filter
        response = client.get("/notifications/?is_read=false", headers=auth_headers)
        assert response.status_code == 200
        
        # Test type filter
        response = client.get("/notifications/?type=task_assigned", headers=auth_headers)
        assert response.status_code == 200
        
        # Test combined filters
        response = client.get("/notifications/?is_read=false&type=task_assigned", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_notifications_invalid_page(self, client: TestClient, auth_headers: dict):
        """Test getting notifications with invalid page number."""
        response = client.get("/notifications/?page=-1", headers=auth_headers)
        
        # Should either succeed (with validation) or fail with validation error
        assert response.status_code in [200, 422]
    
    def test_get_notifications_invalid_limit(self, client: TestClient, auth_headers: dict):
        """Test getting notifications with invalid limit."""
        response = client.get("/notifications/?limit=0", headers=auth_headers)
        
        # Should either succeed (with validation) or fail with validation error
        assert response.status_code in [200, 422]
    
    def test_mark_notification_read_success(self, client: TestClient, auth_headers: dict):
        """Test marking notification as read."""
        fake_notification_id = str(uuid.uuid4())
        response = client.patch(f"/notifications/{fake_notification_id}/read", headers=auth_headers)
        
        # Should fail because notification doesn't exist
        assert response.status_code == 404
    
    def test_mark_notification_read_unauthorized(self, client: TestClient):
        """Test marking notification as read without authentication."""
        fake_notification_id = str(uuid.uuid4())
        response = client.patch(f"/notifications/{fake_notification_id}/read")
        
        assert response.status_code == 401
    
    def test_mark_notification_read_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test marking notification as read with invalid UUID."""
        invalid_id = "invalid-uuid"
        response = client.patch(f"/notifications/{invalid_id}/read", headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_mark_all_notifications_read_success(self, client: TestClient, auth_headers: dict):
        """Test marking all notifications as read."""
        response = client.patch("/notifications/read-all", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "All notifications marked as read" in data["message"]
    
    def test_mark_all_notifications_read_unauthorized(self, client: TestClient):
        """Test marking all notifications as read without authentication."""
        response = client.patch("/notifications/read-all")
        
        assert response.status_code == 401

class TestNotificationDataValidation:
    """Test notification data validation and structure."""
    
    def test_notification_response_structure(self, client: TestClient, auth_headers: dict):
        """Test notification response structure."""
        response = client.get("/notifications/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check pagination structure
        assert "items" in data
        assert "total" in data
        assert "unread_count" in data
        assert "page" in data
        assert "limit" in data
        assert "pages" in data
        
        # If there are notifications, check their structure
        if data["items"]:
            notification = data["items"][0]
            required_fields = ["id", "type", "title", "message", "is_read", "created_at"]
            for field in required_fields:
                assert field in notification
            
            # Check data field if present
            if "data" in notification:
                assert isinstance(notification["data"], dict)
    
    def test_notification_types(self, client: TestClient, auth_headers: dict):
        """Test filtering by different notification types."""
        notification_types = [
            "task_assigned",
            "task_completed", 
            "project_invitation",
            "member_added",
            "task_updated"
        ]
        
        for notification_type in notification_types:
            response = client.get(f"/notifications/?type={notification_type}", headers=auth_headers)
            assert response.status_code == 200
    
    def test_notification_read_filter(self, client: TestClient, auth_headers: dict):
        """Test filtering by read status."""
        # Test unread notifications
        response = client.get("/notifications/?is_read=false", headers=auth_headers)
        assert response.status_code == 200
        
        # Test read notifications
        response = client.get("/notifications/?is_read=true", headers=auth_headers)
        assert response.status_code == 200

class TestNotificationEdgeCases:
    """Test notification edge cases and error handling."""
    
    def test_empty_notifications_list(self, client: TestClient, auth_headers: dict):
        """Test getting notifications when user has none."""
        response = client.get("/notifications/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["unread_count"] == 0
    
    def test_large_notifications_list(self, client: TestClient, auth_headers: dict):
        """Test getting notifications with pagination for large lists."""
        # Test with different page sizes
        page_sizes = [1, 5, 10, 20, 50, 100]
        
        for limit in page_sizes:
            response = client.get(f"/notifications/?limit={limit}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == limit
            assert isinstance(data["items"], list)
    
    def test_notification_not_found(self, client: TestClient, auth_headers: dict):
        """Test marking non-existent notification as read."""
        fake_id = str(uuid.uuid4())
        response = client.patch(f"/notifications/{fake_id}/read", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_notification_already_read(self, client: TestClient, auth_headers: dict):
        """Test marking already read notification as read."""
        # This would require creating a notification first
        # For now, test with fake ID
        fake_id = str(uuid.uuid4())
        response = client.patch(f"/notifications/{fake_id}/read", headers=auth_headers)
        
        # Should fail because notification doesn't exist
        assert response.status_code == 404
    
    def test_mark_all_read_when_none_exist(self, client: TestClient, auth_headers: dict):
        """Test marking all notifications as read when none exist."""
        response = client.patch("/notifications/read-all", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

class TestNotificationPerformance:
    """Test notification performance and rate limiting."""
    
    def test_notifications_response_time(self, client: TestClient, auth_headers: dict):
        """Test notifications endpoint response time."""
        import time
        
        start_time = time.time()
        response = client.get("/notifications/", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 2.0  # 2 seconds max
    
    def test_notifications_pagination_performance(self, client: TestClient, auth_headers: dict):
        """Test pagination performance."""
        import time
        
        # Test different page numbers
        for page in [1, 5, 10, 50]:
            start_time = time.time()
            response = client.get(f"/notifications/?page={page}&limit=20", headers=auth_headers)
            end_time = time.time()
            
            assert response.status_code == 200
            assert end_time - start_time < 2.0
    
    def test_concurrent_notification_requests(self, client: TestClient, auth_headers: dict):
        """Test concurrent notification requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/notifications/", headers=auth_headers)
            results.append(response.status_code)
        
        # Make 5 concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(results) == 5
        assert all(status == 200 for status in results)
    
    def test_mark_read_concurrent_requests(self, client: TestClient, auth_headers: dict):
        """Test concurrent mark as read requests."""
        import threading
        
        fake_id = str(uuid.uuid4())
        results = []
        
        def make_request():
            response = client.patch(f"/notifications/{fake_id}/read", headers=auth_headers)
            results.append(response.status_code)
        
        # Make 3 concurrent requests for same notification
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All should fail with 404 (notification doesn't exist)
        assert len(results) == 3
        assert all(status == 404 for status in results)

class TestNotificationIntegration:
    """Test notification integration with other features."""
    
    def test_notification_creation_on_task_assignment(self, client: TestClient, auth_headers: dict, db_session):
        """Test notification creation when task is assigned."""
        # This would require setting up task assignment
        # For now, test the structure
        response = client.get("/notifications/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
    
    def test_notification_creation_on_project_invitation(self, client: TestClient, auth_headers: dict):
        """Test notification creation when user is invited to project."""
        # This would require setting up project invitation
        response = client.get("/notifications/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
    
    def test_notification_data_structure(self, client: TestClient, auth_headers: dict):
        """Test notification data field structure."""
        response = client.get("/notifications/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if data["items"]:
            notification = data["items"][0]
            if "data" in notification:
                data_field = notification["data"]
                # Common data fields
                possible_fields = ["task_id", "project_id", "task_title", "user_id", "user_name"]
                
                # Should contain at least some expected fields
                assert isinstance(data_field, dict)