import pytest
import os
import sys
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_db
from models import Base

# Override database URL for testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    # Create engine for in-memory SQLite
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(engine):
    """
    Creates a new database session for a test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    # Set testing environment variables
    os.environ["TESTING"] = "true"
    
    # Override get_db dependency
    app.dependency_overrides[get_db] = lambda: db_session
    
    with TestClient(app) as c:
        yield c
    
    # Restore dependency override
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(db_session):
    """Create a test user."""
    from models.user import User
    from utils.auth import get_password_hash
    
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def test_user_token(test_user):
    """Create a valid JWT token for the test user."""
    from utils.auth import create_access_token
    from datetime import timedelta
    
    access_token = create_access_token(
        data={"sub": str(test_user.id)},
        expires_delta=timedelta(minutes=30)
    )
    return access_token
