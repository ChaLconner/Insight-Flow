"""
Tests for routers/files.py

Tests file upload/download authentication.
"""

import pytest
from fastapi.testclient import TestClient

from main import app

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def unauthenticated_client():
    """Test client without authentication."""
    with TestClient(app) as client:
        yield client


# ============================================================================
# Tests for Files Router Authentication
# ============================================================================


class TestFilesAuthentication:
    def test_upload_file_requires_auth(self, unauthenticated_client):
        """Test file upload requires authentication."""
        response = unauthenticated_client.post(
            "/api/v1/files/upload", files={"file": ("test.txt", b"test content", "text/plain")}
        )
        assert response.status_code == 401
