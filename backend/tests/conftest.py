"""
Pytest configuration and fixtures for API testing.
"""
import pytest
import httpx
from typing import Generator, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database import get_db, Base
from main import app
from models.user import User
from services.user_service import UserService

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db():
    """Create database tables for testing."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(db):
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Test user data for registration."""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword123"
    }

@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user in the database."""
    user_service = UserService(db_session)
    from schemas.user import UserCreate
    user_data = UserCreate(
        email="test@example.com",
        name="Test User",
        password="testpassword123"
    )
    return user_service.create_user(user_data)

@pytest.fixture
def auth_headers(test_user) -> Dict[str, str]:
    """Get authentication headers for test user."""
    from utils.auth import create_access_token
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_user(db_session) -> User:
    """Create an admin user for testing."""
    user_service = UserService(db_session)
    from schemas.user import UserCreate
    user_data = UserCreate(
        email="admin@example.com",
        name="Admin User",
        password="adminpassword123"
    )
    return user_service.create_user(user_data)

@pytest.fixture
def admin_headers(admin_user) -> Dict[str, str]:
    """Get authentication headers for admin user."""
    from utils.auth import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    """Sample project data for testing."""
    return {
        "name": "Test Project",
        "description": "A test project for API testing"
    }

@pytest.fixture
def sample_task_data() -> Dict[str, Any]:
    """Sample task data for testing."""
    return {
        "title": "Test Task",
        "description": "A test task for API testing",
        "due_date": "2024-12-31T23:59:59Z"
    }