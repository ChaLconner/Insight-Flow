"""
Tests for routers/files.py and routers/usage.py endpoints.
Integration tests for file upload/download and usage statistics.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import io


class TestFilesRouter:
    """Tests for the files router endpoints."""

    def test_upload_file_requires_auth(self, unauthenticated_client):
        """Test that file upload requires authentication."""
        # Create a mock file
        file_content = b"test content"
        response = unauthenticated_client.post(
            "/api/v1/files/upload",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert response.status_code == 401

    def test_upload_file_success(self, client):
        """Test successful file upload."""
        file_content = b"test file content for upload"
        
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("test_upload.txt", io.BytesIO(file_content), "text/plain")},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "filename" in data
        assert "id" in data
        assert data["url"].startswith("/static/uploads/")

    def test_upload_file_generates_unique_name(self, client):
        """Test that uploaded files get unique names."""
        file_content = b"test content"
        
        response1 = client.post(
            "/api/v1/files/upload",
            files={"file": ("same_name.txt", io.BytesIO(file_content), "text/plain")},
        )
        response2 = client.post(
            "/api/v1/files/upload",
            files={"file": ("same_name.txt", io.BytesIO(file_content), "text/plain")},
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Filenames should be different (UUID-based)
        assert response1.json()["filename"] != response2.json()["filename"]

    def test_upload_file_preserves_extension(self, client):
        """Test that file extension is preserved after upload."""
        file_content = b"test content"
        
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("document.pdf", io.BytesIO(file_content), "application/pdf")},
        )
        
        assert response.status_code == 200
        assert response.json()["filename"].endswith(".pdf")

    def test_delete_file_requires_auth(self, unauthenticated_client):
        """Test that file deletion requires authentication."""
        response = unauthenticated_client.delete(
            "/api/v1/files/delete",
            params={"url": "/static/uploads/test.txt"}
        )
        assert response.status_code == 401

    def test_delete_file_prevents_directory_traversal(self, client):
        """Test that directory traversal is blocked."""
        response = client.delete(
            "/api/v1/files/delete",
            params={"url": "../../../etc/passwd"}
        )
        assert response.status_code == 400
        # Application uses 'message' field in error responses, not 'detail'
        response_data = response.json()
        assert "Invalid" in response_data.get("message", "") or "Invalid" in response_data.get("detail", "")

    def test_delete_nonexistent_file(self, client):
        """Test deleting a file that doesn't exist."""
        response = client.delete(
            "/api/v1/files/delete",
            params={"url": "/static/uploads/nonexistent-file-12345.txt"}
        )
        # Should return 404 or appropriate error
        assert response.status_code in [404, 500]


class TestUsageRouter:
    """Tests for the usage router endpoints."""

    def test_get_usage_stats_requires_auth(self, unauthenticated_client):
        """Test that usage stats requires authentication."""
        response = unauthenticated_client.get("/api/v1/usage/stats")
        assert response.status_code == 401

    def test_get_usage_stats_success(self, client):
        """Test getting usage statistics."""
        response = client.get("/api/v1/usage/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "projects_used" in data
        assert "seats_used" in data
        
        # Values should be non-negative integers
        assert isinstance(data["projects_used"], int)
        assert isinstance(data["seats_used"], int)
        assert data["projects_used"] >= 0
        assert data["seats_used"] >= 1  # At least the user themselves

    def test_usage_stats_new_user(self, client):
        """Test usage stats for a new user with no projects."""
        response = client.get("/api/v1/usage/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # New user should have minimal usage
        # Seats should be at least 1 (the user themselves)
        assert data["seats_used"] >= 1


class TestFilesRouterEdgeCases:
    """Edge case tests for files router."""

    def test_upload_empty_file(self, client):
        """Test uploading an empty file."""
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        # Should fail for empty file
        assert response.status_code == 400

    def test_upload_file_with_special_characters_in_name(self, client):
        """Test uploading a file with special characters in name."""
        file_content = b"test content"
        
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("file with spaces & symbols!.txt", io.BytesIO(file_content), "text/plain")},
        )
        
        # Should succeed - filename is replaced with UUID
        assert response.status_code == 200

    def test_upload_large_file_boundary(self, client):
        """Test uploading a file at reasonable size."""
        # 1KB file
        file_content = b"x" * 1024
        
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("large.txt", io.BytesIO(file_content), "text/plain")},
        )
        
        assert response.status_code == 200


class TestFileOwnership:
    """Tests for file ownership verification."""

    def test_delete_own_file(self, client, db_session, test_user):
        """Test that users can delete their own files."""
        # First upload a file
        file_content = b"my file content"
        upload_response = client.post(
            "/api/v1/files/upload",
            files={"file": ("myfile.txt", io.BytesIO(file_content), "text/plain")},
        )
        
        assert upload_response.status_code == 200
        file_url = upload_response.json()["url"]
        
        # Then delete it
        delete_response = client.delete(
            "/api/v1/files/delete",
            params={"url": file_url}
        )
        
        assert delete_response.status_code == 200
        assert "deleted" in delete_response.json().get("message", "").lower()
