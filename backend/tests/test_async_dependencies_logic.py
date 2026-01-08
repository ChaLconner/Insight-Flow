"""
Tests for async_dependencies.py logic.
Focuses on permission factories and dependency logic.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestAsyncDependenciesLogic:
    """Tests for complex logic in async_dependencies.py."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = uuid.uuid4()
        user.role = "user"
        return user

    @pytest.fixture
    def mock_project(self):
        project = MagicMock()
        project.id = uuid.uuid4()
        project.owner_id = uuid.uuid4()
        return project

    @pytest.mark.asyncio
    async def test_permission_check_factory_logic_admin_bypass(
        self, mock_db, mock_user, mock_project
    ):
        """Test that admin bypasses all checks."""
        from async_dependencies import _create_project_permission

        # Setup admin user
        mock_user.role = "admin"

        permission_check = _create_project_permission(["owner"])

        # We need to mock the inner imports/calls
        with patch("services.async_project_service.AsyncProjectService") as MockService:
            service_instance = MockService.return_value
            service_instance.get_project_by_id = AsyncMock(return_value=mock_project)

            # Since dependencies are injected by FastAPI normally, we call the function directly
            # parsing the arguments as if dependency injection happened
            result = await permission_check(
                project_id=str(mock_project.id), current_user=mock_user, db=mock_db
            )

            assert result == mock_project

    @pytest.mark.asyncio
    async def test_permission_check_factory_logic_owner(self, mock_db, mock_user, mock_project):
        """Test that project owner passes check."""
        from async_dependencies import _create_project_permission

        mock_user.role = "user"
        mock_project.owner_id = mock_user.id

        permission_check = _create_project_permission(["owner"])

        with patch("services.async_project_service.AsyncProjectService") as MockService:
            service_instance = MockService.return_value
            service_instance.get_project_by_id = AsyncMock(return_value=mock_project)

            result = await permission_check(
                project_id=str(mock_project.id), current_user=mock_user, db=mock_db
            )

            assert result == mock_project

    @pytest.mark.asyncio
    async def test_permission_check_factory_logic_member_success(
        self, mock_db, mock_user, mock_project
    ):
        """Test that member with correct role passes."""
        from async_dependencies import _create_project_permission
        from models.project import MemberRole

        mock_user.role = "user"
        mock_project.owner_id = uuid.uuid4()  # Not owner

        permission_check = _create_project_permission(["admin"])  # Require project admin

        with patch("services.async_project_service.AsyncProjectService") as MockService:
            service_instance = MockService.return_value
            service_instance.get_project_by_id = AsyncMock(return_value=mock_project)

            # Mock DB result for member check
            mock_result = MagicMock()
            mock_member = MagicMock()
            mock_member.role = MemberRole.ADMIN
            mock_result.scalars.return_value.first.return_value = mock_member
            mock_db.execute.return_value = mock_result

            result = await permission_check(
                project_id=str(mock_project.id), current_user=mock_user, db=mock_db
            )

            assert result == mock_project

    @pytest.mark.asyncio
    async def test_permission_check_factory_logic_not_member(
        self, mock_db, mock_user, mock_project
    ):
        """Test that non-member fails."""
        from async_dependencies import _create_project_permission

        mock_user.role = "user"
        mock_project.owner_id = uuid.uuid4()

        permission_check = _create_project_permission(["member"])

        with patch("services.async_project_service.AsyncProjectService") as MockService:
            service_instance = MockService.return_value
            service_instance.get_project_by_id = AsyncMock(return_value=mock_project)

            # Mock DB result - no member found
            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = None
            mock_db.execute.return_value = mock_result

            with pytest.raises(HTTPException) as exc:
                await permission_check(
                    project_id=str(mock_project.id), current_user=mock_user, db=mock_db
                )
            assert exc.value.status_code == 403
            assert "Not a member" in exc.value.detail
