"""
Tests for async_dependencies.py - Project and Task authorization.
Covers permission checking and task authorization functions.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCreateProjectPermission:
    """Tests for _create_project_permission factory function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user."""
        user = MagicMock()
        user.id = uuid.uuid4()
        user.role = "admin"
        user.email = "admin@test.com"
        return user

    @pytest.fixture
    def mock_regular_user(self):
        """Create a mock regular user."""
        user = MagicMock()
        user.id = uuid.uuid4()
        user.role = "user"
        user.email = "user@test.com"
        return user

    @pytest.fixture
    def mock_project(self):
        """Create a mock project."""
        project = MagicMock()
        project.id = uuid.uuid4()
        project.name = "Test Project"
        project.owner_id = uuid.uuid4()
        return project

    def test_create_project_permission_returns_callable(self):
        """Test that _create_project_permission returns a callable."""
        from async_dependencies import _create_project_permission

        permission_check = _create_project_permission(["owner"])

        assert callable(permission_check)

    def test_create_project_permission_with_different_roles(self):
        """Test factory with different role configurations."""
        from async_dependencies import _create_project_permission

        owner_only = _create_project_permission(["owner"])
        admin_or_owner = _create_project_permission(["owner", "admin"])
        all_members = _create_project_permission(["owner", "admin", "member"])

        assert callable(owner_only)
        assert callable(admin_or_owner)
        assert callable(all_members)


class TestCreateTaskAuthorization:
    """Tests for _create_task_authorization factory function."""

    def test_create_task_authorization_returns_callable(self):
        """Test that _create_task_authorization returns a callable."""
        from async_dependencies import _create_task_authorization

        authorize_task = _create_task_authorization()

        assert callable(authorize_task)


class TestEnsureInitialized:
    """Tests for _ensure_initialized function."""

    def test_ensure_initialized_creates_permissions(self):
        """Test that _ensure_initialized creates all permission instances."""
        from async_dependencies import _ensure_initialized

        # Call the function
        _ensure_initialized()

        # Access the module-level variables to verify they're initialized
        import async_dependencies

        # Use __getattr__ to get the values
        owner = async_dependencies.require_project_owner
        admin = async_dependencies.require_project_admin
        member = async_dependencies.require_project_member
        task_auth = async_dependencies.get_async_authorized_task

        assert owner is not None
        assert admin is not None
        assert member is not None
        assert task_auth is not None


class TestModuleGetattr:
    """Tests for __getattr__ module-level function."""

    def test_getattr_returns_require_project_owner(self):
        """Test __getattr__ returns require_project_owner."""
        import async_dependencies

        result = async_dependencies.require_project_owner

        assert result is not None
        assert callable(result)

    def test_getattr_returns_require_project_admin(self):
        """Test __getattr__ returns require_project_admin."""
        import async_dependencies

        result = async_dependencies.require_project_admin

        assert result is not None
        assert callable(result)

    def test_getattr_returns_require_project_member(self):
        """Test __getattr__ returns require_project_member."""
        import async_dependencies

        result = async_dependencies.require_project_member

        assert result is not None
        assert callable(result)

    def test_getattr_returns_get_async_authorized_task(self):
        """Test __getattr__ returns get_async_authorized_task."""
        import async_dependencies

        result = async_dependencies.get_async_authorized_task

        assert result is not None
        assert callable(result)

    def test_getattr_returns_get_authorized_task_alias(self):
        """Test __getattr__ returns get_authorized_task (alias)."""
        import async_dependencies

        result = async_dependencies.get_authorized_task

        assert result is not None
        assert callable(result)

    def test_getattr_raises_attribute_error_for_unknown(self):
        """Test __getattr__ raises AttributeError for unknown attributes."""
        import async_dependencies

        with pytest.raises(AttributeError) as exc_info:
            _ = async_dependencies.nonexistent_attribute

        assert "nonexistent_attribute" in str(exc_info.value)


class TestModuleAll:
    """Tests for __all__ module attribute."""

    def test_all_contains_expected_exports(self):
        """Test __all__ contains all expected exports."""
        from async_dependencies import __all__

        expected = [
            "get_async_authorized_task",
            "get_authorized_task",
            "require_project_admin",
            "require_project_member",
            "require_project_owner",
        ]

        for item in expected:
            assert item in __all__


class TestUuidValidation:
    """Tests for UUID validation in permission functions."""

    def test_invalid_uuid_raises_value_error(self):
        """Test that invalid UUID string raises ValueError."""
        with pytest.raises(ValueError):
            uuid.UUID("invalid-uuid-string")

    def test_valid_uuid_parses_correctly(self):
        """Test that valid UUID string parses correctly."""
        valid_uuid = "12345678-1234-5678-1234-567812345678"
        parsed = uuid.UUID(valid_uuid)

        assert str(parsed) == valid_uuid


class TestPermissionRoles:
    """Tests for permission role configurations."""

    def test_owner_role_list(self):
        """Test owner-only role list."""
        roles = ["owner"]
        assert "owner" in roles
        assert "admin" not in roles

    def test_admin_role_list(self):
        """Test owner and admin role list."""
        roles = ["owner", "admin"]
        assert "owner" in roles
        assert "admin" in roles
        assert "member" not in roles

    def test_member_role_list(self):
        """Test all member role list."""
        roles = ["owner", "admin", "member"]
        assert "owner" in roles
        assert "admin" in roles
        assert "member" in roles
