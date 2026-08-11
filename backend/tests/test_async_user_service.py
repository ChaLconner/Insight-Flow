"""
Async Unit tests for AsyncUserService.
"""

import uuid
from unittest.mock import patch

import pytest

from models.user import User
from schemas.user import UserCreate, UserLogin, UserUpdate


class TestAsyncUserService:
    """Test cases for AsyncUserService."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, db_session, async_user_service, async_session):
        """Test successful user creation."""
        user_data = UserCreate(
            email="newuser@example.com", password="StrongPassword123!", name="New User"
        )

        user = await async_user_service.create_user(user_data)

        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.name == "New User"
        assert user.is_active is True
        assert user.hashed_password != "StrongPassword123!"  # Should be hashed

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, db_session, async_user_service):
        """Test creating user with duplicate email fails."""
        user_data = UserCreate(
            email="duplicate@example.com", password="StrongPassword123!", name="User One"
        )
        await async_user_service.create_user(user_data)

        # Try to create another user with same email
        duplicate_data = UserCreate(
            email="duplicate@example.com", password="AnotherPassword123!", name="User Two"
        )

        with pytest.raises(ValueError, match=r"already registered|[Aa]lready exists|[Dd]uplicate"):
            await async_user_service.create_user(duplicate_data)

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session, async_user_service):
        """Test getting user by email."""
        user_data = UserCreate(
            email="findme@example.com", password="StrongPassword123!", name="Find Me"
        )
        created_user = await async_user_service.create_user(user_data)

        found_user = await async_user_service.get_user_by_email("findme@example.com")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "findme@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, db_session, async_user_service):
        """Test getting non-existent user by email."""
        user = await async_user_service.get_user_by_email("notexist@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session, async_user_service):
        """Test getting user by ID."""
        user_data = UserCreate(
            email="byid@example.com", password="StrongPassword123!", name="By ID"
        )
        created_user = await async_user_service.create_user(user_data)

        found_user = await async_user_service.get_user_by_id(created_user.id)

        assert found_user is not None
        assert found_user.email == "byid@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, db_session, async_user_service):
        """Test getting non-existent user by ID."""
        fake_id = uuid.uuid4()
        user = await async_user_service.get_user_by_id(fake_id)
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session, async_user_service):
        """Test successful authentication."""
        user_data = UserCreate(
            email="auth@example.com", password="StrongPassword123!", name="Auth User"
        )
        await async_user_service.create_user(user_data)

        login_data = UserLogin(email="auth@example.com", password="StrongPassword123!")

        authenticated_user = await async_user_service.authenticate_user(login_data)

        assert authenticated_user is not None
        assert authenticated_user.email == "auth@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session, async_user_service):
        """Test authentication with wrong password."""
        user_data = UserCreate(
            email="wrongpass@example.com", password="StrongPassword123!", name="Wrong Pass"
        )
        await async_user_service.create_user(user_data)

        login_data = UserLogin(email="wrongpass@example.com", password="WrongPassword!")

        authenticated_user = await async_user_service.authenticate_user(login_data)
        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_update_user_success(self, db_session, async_user_service):
        """Test successful user update."""
        user_data = UserCreate(
            email="update@example.com", password="StrongPassword123!", name="Original Name"
        )
        created_user = await async_user_service.create_user(user_data)

        update_data = UserUpdate(name="Updated Name")
        updated_user = await async_user_service.update_user(created_user.id, update_data)

        assert updated_user is not None
        assert updated_user.name == "Updated Name"
        assert updated_user.email == "update@example.com"  # Unchanged

    @pytest.mark.asyncio
    async def test_change_password_success(self, db_session, async_user_service):
        """Test changing password."""
        user_data = UserCreate(
            email="changepass@example.com", password="OldPassword123!", name="Change Pass"
        )
        created_user = await async_user_service.create_user(user_data)

        result = await async_user_service.change_password(
            created_user.id, "OldPassword123!", "NewPassword123!"
        )

        assert result is True

        # Verify new password works
        login_data = UserLogin(email="changepass@example.com", password="NewPassword123!")
        authenticated = await async_user_service.authenticate_user(login_data)
        assert authenticated is not None

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, db_session, async_user_service):
        """Test changing password with wrong current password."""
        user_data = UserCreate(
            email="wrongcurrent@example.com", password="CurrentPassword123!", name="Test User"
        )
        created_user = await async_user_service.create_user(user_data)

        with pytest.raises(ValueError, match="Incorrect"):
            await async_user_service.change_password(
                created_user.id, "WrongCurrentPassword!", "NewPassword123!"
            )

    @pytest.mark.asyncio
    async def test_verify_password(self, db_session, async_user_service):
        """Test password verification."""
        user_data = UserCreate(
            email="verify@example.com", password="TestPassword123!", name="Verify User"
        )
        created_user = await async_user_service.create_user(user_data)

        # Correct password
        result = await async_user_service.verify_password(
            "TestPassword123!", created_user.hashed_password
        )
        assert result is True

        # Wrong password
        result = await async_user_service.verify_password(
            "WrongPassword!", created_user.hashed_password
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_hash_password(self, db_session, async_user_service):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = await async_user_service.hash_password(password)

        assert len(hashed) > 20  # Hashed passwords are longer

    @pytest.mark.asyncio
    async def test_create_user_integrity_error(self, async_user_service):
        """Test handling of IntegrityError during creation."""
        from unittest.mock import AsyncMock, MagicMock

        from sqlalchemy.exc import IntegrityError

        from services.async_user_service import AsyncUserService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock(side_effect=IntegrityError(None, None, Exception("Error")))
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()
        # Mock execute for get_user_by_email checks if unique
        # Actually create_user logic doesn't call get_user_by_email explicitly, it relies on DB constraints?
        # Let's check logic: create_user lines 65-136. It doesn't check uniqueness before insert.
        # But it does `await self.hash_password(user_data.password)`.
        # This calls `loop.run_in_executor`. Mocks handles this if we don't mock hash_password.

        service = AsyncUserService(mock_db)
        # We need to mock hash_password to avoid password executor issues/slowness
        service.hash_password = AsyncMock(return_value="hashed_pw")

        user_data = UserCreate(email="fail@test.com", password="StrongPassword123!")

        with pytest.raises(ValueError, match="User creation failed"):
            await service.create_user(user_data)

    @pytest.mark.asyncio
    async def test_update_user_integrity_error(self, async_user_service):
        from unittest.mock import AsyncMock, MagicMock

        from sqlalchemy.exc import IntegrityError

        from services.async_user_service import AsyncUserService

        mock_db = MagicMock()

        # Mock get_user_by_id result
        user_mock = User(
            id=uuid.uuid4(), email="test@test.com", name="Old"
        )  # Use real model or strict mock

        # Result mock
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = user_mock

        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.commit = AsyncMock(side_effect=IntegrityError(None, None, Exception("Error")))
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()

        service = AsyncUserService(mock_db)

        update_data = UserUpdate(name="New")
        with pytest.raises(ValueError, match="User update failed"):
            await service.update_user(uuid.uuid4(), update_data)

    @pytest.mark.asyncio
    async def test_invite_user(self, async_user_service):
        from unittest.mock import AsyncMock, MagicMock

        from schemas.user import UserInvite

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()  # get_user_by_email
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # return user
        user = User(email="invite@test.com", role="member", is_active=False)
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = user
        mock_db.execute.return_value = result_mock

        from services.async_user_service import AsyncUserService

        service = AsyncUserService(mock_db)

        invite = UserInvite(email="invite@test.com", role="admin")
        result = await service.invite_user(invite, actor_role="admin")

        assert result.role == "admin"
        assert result.is_active is True
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_manager_cannot_invite_privileged_role(self, async_user_service):
        from schemas.user import UserInvite

        invite = UserInvite(email="invite@test.com", role="admin")

        with pytest.raises(ValueError, match="privileged roles"):
            await async_user_service.invite_user(invite, actor_role="manager")

    @pytest.mark.asyncio
    async def test_verify_email_legacy(self, async_user_service):
        from unittest.mock import AsyncMock, MagicMock

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        # First call returns None (hashed token mismatch)
        # Second call returns User (legacy token match)

        user = User(email="legacy@test.com", verification_token="legacy_token", is_verified=False)

        # Side effect for execute: first call returns empty, second returns user
        empty_result = MagicMock()
        empty_result.scalars.return_value.first.return_value = None

        user_result = MagicMock()
        user_result.scalars.return_value.first.return_value = user

        mock_db.execute.side_effect = [empty_result, user_result]
        mock_db.commit = AsyncMock()

        from services.async_user_service import AsyncUserService

        service = AsyncUserService(mock_db)

        # We need to mock _hash_token to ensure it doesn't match legacy token if we control it
        # But implementation hashes input token.

        result = await service.verify_email("legacy_token")

        assert result is True
        assert user.is_verified is True
        assert user.verification_token is None

    @pytest.mark.asyncio
    async def test_resend_verification_email(self, async_user_service):
        from unittest.mock import AsyncMock, MagicMock

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        user = User(email="resend@test.com", is_verified=False)
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = user
        mock_db.execute.return_value = result_mock
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        from services.async_user_service import AsyncUserService

        service = AsyncUserService(mock_db)

        with patch(
            "services.async_user_service.enqueue_job", new_callable=AsyncMock
        ) as mock_enqueue:
            result = await service.resend_verification_email("resend@test.com")
            assert result is True
            mock_enqueue.assert_awaited_once()
            assert user.verification_token is not None
