"""
Async Unit tests for AsyncUserService.
"""
import pytest
import uuid
from models.user import User
from schemas.user import UserCreate, UserUpdate, UserLogin


class TestAsyncUserService:
    """Test cases for AsyncUserService."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, db_session, async_user_service, async_session):
        """Test successful user creation."""
        user_data = UserCreate(
            email="newuser@example.com",
            password="StrongPassword123!",
            name="New User"
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
            email="duplicate@example.com",
            password="StrongPassword123!",
            name="User One"
        )
        await async_user_service.create_user(user_data)
        
        # Try to create another user with same email
        duplicate_data = UserCreate(
            email="duplicate@example.com",
            password="AnotherPassword123!",
            name="User Two"
        )
        
        with pytest.raises(ValueError, match="already registered|[Aa]lready exists|[Dd]uplicate"):
            await async_user_service.create_user(duplicate_data)

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session, async_user_service):
        """Test getting user by email."""
        user_data = UserCreate(
            email="findme@example.com",
            password="StrongPassword123!",
            name="Find Me"
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
            email="byid@example.com",
            password="StrongPassword123!",
            name="By ID"
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
            email="auth@example.com",
            password="StrongPassword123!",
            name="Auth User"
        )
        await async_user_service.create_user(user_data)
        
        login_data = UserLogin(
            email="auth@example.com",
            password="StrongPassword123!"
        )
        
        authenticated_user = await async_user_service.authenticate_user(login_data)
        
        assert authenticated_user is not None
        assert authenticated_user.email == "auth@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session, async_user_service):
        """Test authentication with wrong password."""
        user_data = UserCreate(
            email="wrongpass@example.com",
            password="StrongPassword123!",
            name="Wrong Pass"
        )
        await async_user_service.create_user(user_data)
        
        login_data = UserLogin(
            email="wrongpass@example.com",
            password="WrongPassword!"
        )
        
        authenticated_user = await async_user_service.authenticate_user(login_data)
        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_update_user_success(self, db_session, async_user_service):
        """Test successful user update."""
        user_data = UserCreate(
            email="update@example.com",
            password="StrongPassword123!",
            name="Original Name"
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
            email="changepass@example.com",
            password="OldPassword123!",
            name="Change Pass"
        )
        created_user = await async_user_service.create_user(user_data)
        
        result = await async_user_service.change_password(
            created_user.id,
            "OldPassword123!",
            "NewPassword123!"
        )
        
        assert result is True
        
        # Verify new password works
        login_data = UserLogin(
            email="changepass@example.com",
            password="NewPassword123!"
        )
        authenticated = await async_user_service.authenticate_user(login_data)
        assert authenticated is not None

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, db_session, async_user_service):
        """Test changing password with wrong current password."""
        user_data = UserCreate(
            email="wrongcurrent@example.com",
            password="CurrentPassword123!",
            name="Test User"
        )
        created_user = await async_user_service.create_user(user_data)
        
        with pytest.raises(ValueError, match="Incorrect"):
            await async_user_service.change_password(
                created_user.id,
                "WrongCurrentPassword!",
                "NewPassword123!"
            )

    @pytest.mark.asyncio
    async def test_verify_password(self, db_session, async_user_service):
        """Test password verification."""
        user_data = UserCreate(
            email="verify@example.com",
            password="TestPassword123!",
            name="Verify User"
        )
        created_user = await async_user_service.create_user(user_data)
        
        # Correct password
        result = await async_user_service.verify_password("TestPassword123!", created_user.hashed_password)
        assert result is True
        
        # Wrong password
        result = await async_user_service.verify_password("WrongPassword!", created_user.hashed_password)
        assert result is False

    @pytest.mark.asyncio
    async def test_hash_password(self, db_session, async_user_service):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = await async_user_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 20  # Hashed passwords are longer
