"""
Unit tests for UserService.
"""
import pytest
import uuid
from models.user import User
from services.user_service import UserService
from schemas.user import UserCreate, UserUpdate, UserLogin


class TestUserService:
    """Test cases for UserService."""

    @pytest.fixture
    def user_service(self, db_session):
        """Create UserService instance."""
        return UserService(db_session)

    def test_create_user_success(self, db_session, user_service):
        """Test successful user creation."""
        user_data = UserCreate(
            email="newuser@example.com",
            password="StrongPassword123!",
            name="New User"
        )
        
        user = user_service.create_user(user_data)
        
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.name == "New User"
        assert user.is_active is True
        assert user.hashed_password != "StrongPassword123!"  # Should be hashed

    def test_create_user_duplicate_email(self, db_session, user_service):
        """Test creating user with duplicate email fails."""
        user_data = UserCreate(
            email="duplicate@example.com",
            password="StrongPassword123!",
            name="ผู้ใช้หนึ่ง"
        )
        user_service.create_user(user_data)
        
        # Try to create another user with same email
        duplicate_data = UserCreate(
            email="duplicate@example.com",
            password="AnotherPassword123!",
            name="ผู้ใช้สอง"
        )
        
        with pytest.raises(ValueError, match="already registered|[Aa]lready exists|[Dd]uplicate"):
            user_service.create_user(duplicate_data)

    def test_get_user_by_email(self, db_session, user_service):
        """Test getting user by email."""
        user_data = UserCreate(
            email="findme@example.com",
            password="StrongPassword123!",
            name="Find Me"
        )
        created_user = user_service.create_user(user_data)
        
        found_user = user_service.get_user_by_email("findme@example.com")
        
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "findme@example.com"

    def test_get_user_by_email_not_found(self, db_session, user_service):
        """Test getting non-existent user by email."""
        user = user_service.get_user_by_email("notexist@example.com")
        assert user is None

    def test_get_user_by_id(self, db_session, user_service):
        """Test getting user by ID."""
        user_data = UserCreate(
            email="byid@example.com",
            password="StrongPassword123!",
            name="By ID"
        )
        created_user = user_service.create_user(user_data)
        
        found_user = user_service.get_user_by_id(created_user.id)
        
        assert found_user is not None
        assert found_user.email == "byid@example.com"

    def test_get_user_by_id_not_found(self, db_session, user_service):
        """Test getting non-existent user by ID."""
        fake_id = uuid.uuid4()
        user = user_service.get_user_by_id(fake_id)
        assert user is None

    def test_authenticate_user_success(self, db_session, user_service):
        """Test successful authentication."""
        user_data = UserCreate(
            email="auth@example.com",
            password="StrongPassword123!",
            name="Auth User"
        )
        user_service.create_user(user_data)
        
        login_data = UserLogin(
            email="auth@example.com",
            password="StrongPassword123!"
        )
        
        authenticated_user = user_service.authenticate_user(login_data)
        
        assert authenticated_user is not None
        assert authenticated_user.email == "auth@example.com"

    def test_authenticate_user_wrong_password(self, db_session, user_service):
        """Test authentication with wrong password."""
        user_data = UserCreate(
            email="wrongpass@example.com",
            password="StrongPassword123!",
            name="Wrong Pass"
        )
        user_service.create_user(user_data)
        
        login_data = UserLogin(
            email="wrongpass@example.com",
            password="WrongPassword!"
        )
        
        authenticated_user = user_service.authenticate_user(login_data)
        assert authenticated_user is None

    def test_authenticate_user_not_found(self, db_session, user_service):
        """Test authentication with non-existent user."""
        login_data = UserLogin(
            email="notexist@example.com",
            password="SomePassword123!"
        )
        
        authenticated_user = user_service.authenticate_user(login_data)
        assert authenticated_user is None

    def test_update_user_success(self, db_session, user_service):
        """Test successful user update."""
        user_data = UserCreate(
            email="update@example.com",
            password="StrongPassword123!",
            name="Original Name"
        )
        created_user = user_service.create_user(user_data)
        
        update_data = UserUpdate(name="Updated Name")
        updated_user = user_service.update_user(created_user.id, update_data)
        
        assert updated_user is not None
        assert updated_user.name == "Updated Name"
        assert updated_user.email == "update@example.com"  # Unchanged

    def test_update_user_not_found(self, db_session, user_service):
        """Test updating non-existent user."""
        fake_id = uuid.uuid4()
        update_data = UserUpdate(name="New Name")
        
        # UserService.update_user raises ValueError if user is not found
        with pytest.raises(ValueError, match="not found"):
            user_service.update_user(fake_id, update_data)

    def test_delete_user_success(self, db_session, user_service):
        """Test successful user deletion."""
        user_data = UserCreate(
            email="delete@example.com",
            password="StrongPassword123!",
            name="To Delete"
        )
        created_user = user_service.create_user(user_data)
        user_id = created_user.id
        
        result = user_service.delete_user(user_id)
        
        assert result is True
        assert user_service.get_user_by_id(user_id) is None

    def test_delete_user_not_found(self, db_session, user_service):
        """Test deleting non-existent user."""
        fake_id = uuid.uuid4()
        # UserService.delete_user raises ValueError if user not found
        with pytest.raises(ValueError, match="not found"):
            user_service.delete_user(fake_id)

    def test_search_users(self, db_session, user_service):
        """Test searching users by name or email."""
        # Create multiple users with valid Thai name format
        for i in range(3):
            user_data = UserCreate(
                email=f"searchtest{i}@example.com",
                password="StrongPassword123!",
                name=f"ผู้ใช้ทดสอบ"
            )
            user_service.create_user(user_data)
        
        # Search by email
        results = user_service.search_users("searchtest")
        assert len(results) >= 1

    def test_get_users_pagination(self, db_session, user_service):
        """Test getting users with pagination."""
        # Create multiple users with valid name format
        for i in range(5):
            user_data = UserCreate(
                email=f"pagetest{i}@example.com",
                password="StrongPassword123!",
                name="ผู้ใช้ทดสอบ"
            )
            user_service.create_user(user_data)
        
        # Get first page
        users = user_service.get_users(skip=0, limit=3)
        assert len(users) >= 3
        
        # Get with limit
        users = user_service.get_users(skip=3, limit=3)
        assert len(users) >= 2

    def test_change_password_success(self, db_session, user_service):
        """Test changing password."""
        user_data = UserCreate(
            email="changepass@example.com",
            password="OldPassword123!",
            name="Change Pass"
        )
        created_user = user_service.create_user(user_data)
        
        result = user_service.change_password(
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
        authenticated = user_service.authenticate_user(login_data)
        assert authenticated is not None

    def test_change_password_wrong_current(self, db_session, user_service):
        """Test changing password with wrong current password."""
        user_data = UserCreate(
            email="wrongcurrent@example.com",
            password="CurrentPassword123!",
            name="ผู้ใช้ทดสอบ"
        )
        created_user = user_service.create_user(user_data)
        
        with pytest.raises(ValueError, match="Incorrect"):
            user_service.change_password(
                created_user.id,
                "WrongCurrentPassword!",
                "NewPassword123!"
            )

    def test_verify_password(self, db_session, user_service):
        """Test password verification."""
        user_data = UserCreate(
            email="verify@example.com",
            password="TestPassword123!",
            name="Verify User"
        )
        created_user = user_service.create_user(user_data)
        
        # Correct password
        assert user_service.verify_password("TestPassword123!", created_user.hashed_password) is True
        
        # Wrong password
        assert user_service.verify_password("WrongPassword!", created_user.hashed_password) is False

    def test_hash_password(self, db_session, user_service):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = user_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 20  # Hashed passwords are longer
