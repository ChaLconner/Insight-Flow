"""
Tests for routers/files.py and routers/usage.py endpoints.
Integration tests for file upload/download and usage statistics.
"""

import io
import os
import uuid
from unittest.mock import AsyncMock, MagicMock

from database import get_async_db
from main import app


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
            "/api/v1/files/delete", params={"url": "/static/uploads/test.txt"}
        )
        assert response.status_code == 401

    def test_get_file_info_requires_auth(self, unauthenticated_client):
        """Test that file info requires authentication."""
        response = unauthenticated_client.get(
            "/api/v1/files/info", params={"url": "/static/uploads/test.txt"}
        )
        assert response.status_code == 401

    def test_get_file_info_success(self, client):
        """Test getting metadata for an uploaded file."""
        file_content = b"file info content"
        upload_response = client.post(
            "/api/v1/files/upload",
            files={"file": ("info.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert upload_response.status_code == 200

        response = client.get("/api/v1/files/info", params={"url": upload_response.json()["url"]})

        assert response.status_code == 200
        data = response.json()
        assert data["url"] == upload_response.json()["url"]
        assert data["filename"] == "info.txt"
        assert data["size_bytes"] == len(file_content)
        assert data["mime_type"] == "text/plain"
        assert data["exists"] is True

    def test_get_file_info_prevents_directory_traversal(self, client):
        """Test that file info blocks directory traversal."""
        response = client.get("/api/v1/files/info", params={"url": "../../../etc/passwd"})
        assert response.status_code == 400

    def test_get_file_info_missing_file(self, client):
        """Test getting metadata for a missing file."""
        response = client.get(
            "/api/v1/files/info", params={"url": "/static/uploads/missing-info-file.txt"}
        )
        assert response.status_code == 404

    def test_delete_file_prevents_directory_traversal(self, client):
        """Test that directory traversal is blocked."""
        response = client.delete("/api/v1/files/delete", params={"url": "../../../etc/passwd"})
        assert response.status_code == 400
        # Application uses 'message' field in error responses, not 'detail'
        response_data = response.json()
        assert "Invalid" in response_data.get("message", "") or "Invalid" in response_data.get(
            "detail", ""
        )

    def test_delete_nonexistent_file(self, client):
        """Test deleting a file that doesn't exist."""
        response = client.delete(
            "/api/v1/files/delete", params={"url": "/static/uploads/nonexistent-file-12345.txt"}
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
            files={
                "file": ("file with spaces & symbols!.txt", io.BytesIO(file_content), "text/plain")
            },
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
        delete_response = client.delete("/api/v1/files/delete", params={"url": file_url})

        assert delete_response.status_code == 200
        assert "deleted" in delete_response.json().get("message", "").lower()

    def test_delete_other_user_file(self, client, admin_token, db_session):
        """Test that users cannot delete files owned by others."""
        # Mock DB to return a file owned by someone else
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # Scenario: File found, but owned by other_id
        other_id = uuid.uuid4()
        # Ensure we don't accidentally match test_user.id
        # Client fixture user has ID? usually randomized or fixed.
        # But file.user_id just needs to be different.

        mock_file = MagicMock()
        mock_file.user_id = other_id
        mock_file.filename = "secret.txt"

        mock_result.scalars.return_value.first.return_value = mock_file
        mock_session.execute.return_value = mock_result

        app.dependency_overrides[get_async_db] = lambda: mock_session

        # Call delete
        # Note: Logic also checks os.path.exists if not in DB?
        # Or if in DB, checks owner.
        # We simulate "In DB" by returning file.

        response = client.delete(
            "/api/v1/files/delete", params={"url": "/static/uploads/secret.txt"}
        )

        assert response.status_code == 403

        del app.dependency_overrides[get_async_db]

    def test_delete_file_not_found_db(self, client):
        """Test deletion where file exists on disk but not in DB (should fail or handle gracefully)."""
        # This tests the logic: if db_file is None
        # But wait, the code checks path validity first.
        # Logic:
        # 1. Validate path
        # 2. Check DB -> if found, check owner.
        # 3. If NOT found in DB, it proceeds to check os.path.exists and delete?
        # Let's check code:
        # if db_file: ... check owner ...
        # if os.path.exists(path): ... delete ... return success
        # else: raise 404

        # So we create a file on disk manually
        filename = "ghost_file.txt"
        os.makedirs("static/uploads", exist_ok=True)
        with open(f"static/uploads/{filename}", "w") as f:
            f.write("ghost")

        url = f"/static/uploads/{filename}"

        delete_response = client.delete("/api/v1/files/delete", params={"url": url})

        assert delete_response.status_code == 200
        assert not os.path.exists(f"static/uploads/{filename}")

    def test_delete_file_path_traversal_payload(self, client):
        """Test delete with various malicious payloads."""
        payloads = [
            "../etc/passwd",
            "static/uploads/../secret.txt",
            "..\\windows\\system32",
        ]
        for payload in payloads:
            response = client.delete("/api/v1/files/delete", params={"url": payload})
            assert response.status_code == 400

        # Test absolute path which is sanitized to basename -> Not found (404)
        response = client.delete("/api/v1/files/delete", params={"url": "/etc/passwd"})
        # Should be 404 because basename is 'passwd', looked up in safe dir, not found
        assert response.status_code == 404


class TestUsageRouterExtended:
    """Extended tests for usage router."""

    def test_usage_stats_with_data(self, client, db_session, test_user):
        """Test usage stats when user has projects."""
        mock_session = AsyncMock()

        # Mock results for sequence of calls
        # 1. Count Projects
        # 2. Count Members

        # Use side_effect to return different results for calls
        mock_result_proj = MagicMock()
        mock_result_proj.scalar.return_value = 5  # projects

        mock_result_memb = MagicMock()
        mock_result_memb.scalar.return_value = 10  # members

        mock_session.execute = AsyncMock(
            side_effect=[
                # We might need to handle exact call order or use execute.return_value logic
                # But simplistic appraoch: if we mock execute to assume success
                # Actually scalar calls:
                # await db.scalar(select(func.count)...)
                # MockAsyncSession execute->Result.
                # But here we use AsyncMock for session.scalar directly if code uses db.scalar
                # Code uses: `projects_count = await db.scalar(...)`
            ]
        )

        # If code uses `db.scalar(...)`, we mock scalar directly
        mock_session.scalar = AsyncMock(side_effect=[5, 10])

        app.dependency_overrides[get_async_db] = lambda: mock_session

        response = client.get("/api/v1/usage/stats")
        assert response.status_code == 200
        data = response.json()

        assert data["projects_used"] == 5
        assert data["seats_used"] == 10

        del app.dependency_overrides[get_async_db]
