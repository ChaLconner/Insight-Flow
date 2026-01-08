"""
Test fixtures for backend tests.
Uses mock sessions and direct authentication override.
"""

import os
import sys
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

# Add backend to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set testing environment BEFORE importing app
os.environ["TESTING"] = "true"

# Import models FIRST (before Base is used elsewhere)
from models import Base
from models.user import User


@pytest.fixture(scope="session")
def test_engine():
    """Create engine for in-memory SQLite - session scoped for efficiency."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Creates a new database session for each test.
    Uses nested transaction for isolation and rollback.
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_user(db_session) -> User:
    """Create a test user for each test."""
    from utils.auth import get_password_hash

    # Check if user already exists
    existing = db_session.query(User).filter_by(email="test@example.com").first()
    if existing:
        return existing

    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        name="Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user_token(test_user) -> str:
    """Create a valid JWT token for test user."""
    from datetime import timedelta

    from utils.auth import create_access_token

    access_token = create_access_token(
        data={"sub": str(test_user.id)}, expires_delta=timedelta(minutes=30)
    )
    return access_token


@pytest.fixture(scope="function")
def admin_user(db_session) -> User:
    """Create an admin user for testing."""
    from utils.auth import get_password_hash

    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        name="Admin User",
        is_active=True,
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_token(admin_user) -> str:
    """Create a valid JWT token for admin user."""
    from datetime import timedelta

    from utils.auth import create_access_token

    access_token = create_access_token(
        data={"sub": str(admin_user.id)}, expires_delta=timedelta(minutes=30)
    )
    return access_token


class MockAsyncSession:
    """
    Wrapper that makes sync session work in async context.
    Implements same interface as AsyncSession.
    """

    def __init__(self, sync_session: Session):
        self._session = sync_session

    async def execute(self, stmt, *args, **kwargs):
        """Execute a statement."""
        return self._session.execute(stmt, *args, **kwargs)

    async def commit(self):
        """Commit transaction."""
        self._session.commit()

    async def rollback(self):
        """Rollback transaction."""
        self._session.rollback()

    async def close(self):
        """Close session."""
        pass

    async def refresh(self, obj):
        """Refresh an object from database."""
        self._session.refresh(obj)

    def add(self, obj):
        """Add an object to session."""
        self._session.add(obj)

    async def delete(self, obj):
        """Delete an object from session."""
        self._session.delete(obj)

    async def get(self, entity, ident):
        """Get an entity by primary key."""
        return self._session.get(entity, ident)

    async def scalar(self, stmt, *args, **kwargs):
        """Execute a statement and return scalar result."""
        result = self._session.execute(stmt, *args, **kwargs)
        return result.scalar()

    async def flush(self):
        """Flush changes to database."""
        self._session.flush()

    def add_all(self, instances):
        """Add multiple objects."""
        self._session.add_all(instances)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.fixture(scope="function")
def async_session(db_session) -> MockAsyncSession:
    """Create a mock async session wrapper around sync session."""
    return MockAsyncSession(db_session)


# Mock init_database globally for all tests to prevent actual DB connection during lifespan
@pytest.fixture(autouse=True)
def mock_app_dependencies(db_session):
    """Automatically mock startup dependencies for all tests."""
    from database import get_async_db
    from main import app

    # Global override for tests that don't use 'client' fixture
    mock_session_global = MockAsyncSession(db_session)

    async def override_get_async_db_global():
        yield mock_session_global

    app.dependency_overrides[get_async_db] = override_get_async_db_global

    with patch("database.init_database", new_callable=AsyncMock):
        with patch("main.init_database", new_callable=AsyncMock):
            with patch("services.scheduler.start_scheduler", return_value=None):
                with patch("services.scheduler.shutdown_scheduler", return_value=None):
                    yield

    # Cleanup if not already cleared
    app.dependency_overrides.pop(get_async_db, None)


@pytest.fixture(scope="function")
def client(db_session, test_user):
    """
    Test client with authentication overrides.
    All async dependencies are mocked to use sync session.
    """
    from database import get_async_db
    from dependencies.auth import get_current_active_user, get_current_user
    from main import app

    # Create mock async session
    mock_async_session = MockAsyncSession(db_session)

    # Override async db - must be async generator
    async def override_get_async_db():
        yield mock_async_session

    # Override auth - IMPORTANT: match the exact signature of the original
    # get_current_user expects (request, db, token) but we can simplify since
    # we just need to return test_user
    async def override_get_current_user(request=None, db=None, token=None):
        return test_user

    async def override_get_current_active_user(current_user=None):
        return test_user

    # Apply overrides
    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    # Use TestClient with context manager to trigger lifespan (with mocks)
    with TestClient(app) as c:
        yield c

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def unauthenticated_client(db_session):
    """
    Test client WITHOUT authentication overrides.
    Useful for testing auth-required endpoints return 401.
    """
    from database import get_async_db
    from main import app

    mock_async_session = MockAsyncSession(db_session)

    async def override_get_async_db():
        yield mock_async_session

    app.dependency_overrides[get_async_db] = override_get_async_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ===========================================
# Async Service Fixtures
# ===========================================


@pytest.fixture(scope="function")
def async_user_service(async_session):
    """Create async user service for tests."""
    from services.async_user_service import AsyncUserService

    return AsyncUserService(async_session)


@pytest.fixture(scope="function")
def async_project_service(async_session):
    """Create async project service for tests."""
    from services.async_project_service import AsyncProjectService

    return AsyncProjectService(async_session)


@pytest.fixture(scope="function")
def async_task_service(async_session):
    """Create async task service for tests."""
    from services.async_task_service import AsyncTaskService

    return AsyncTaskService(async_session)


@pytest.fixture(scope="function")
def async_dashboard_service(async_session):
    """Create async dashboard service for tests."""
    from services.async_dashboard_service import AsyncDashboardService

    return AsyncDashboardService(async_session)


@pytest.fixture(scope="function")
def async_analytics_service(async_session):
    """Create async analytics service for tests."""
    from services.async_analytics_service import AsyncAnalyticsService

    return AsyncAnalyticsService(async_session)


@pytest.fixture(autouse=True)
def mock_payment_lock_manager():
    """
    Force use of InMemoryLockManager for all tests to prevent
    Redis connection sharing across event loops.
    """
    from security.distributed_locks import InMemoryLockManager, reset_lock_manager, set_lock_manager

    # Force in-memory lock
    manager = InMemoryLockManager()
    set_lock_manager(manager)

    yield

    # Cleanup
    reset_lock_manager()
