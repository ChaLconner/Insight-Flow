"""
Database configuration for Insight-Flow application.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base
import ssl
import logging
from contextlib import contextmanager

# Load environment variables from .env file
load_dotenv()

# Use Neon PostgreSQL database from environment variable
database_url = os.getenv("DATABASE_URL", "").strip()

# Check for empty or placeholder URL
if not database_url or "user:password@localhost" in database_url:
    raise ValueError(
        "DATABASE_URL environment variable is not set or is using a placeholder. "
        "Please configure your database connection in the .env file."
    )

# Convert to pg8000 format if needed (since pg8000 is installed)
# We force pg8000 to ensure consistency and avoid driver issues, but allow opting out.
if os.getenv("DB_FORCE_PG8000", "true").lower() == "true":
    if not database_url.startswith("postgresql+pg8000://"):
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+pg8000://", 1)
        elif database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+pg8000://", 1)

# Prepare connection arguments
connect_args = {
    "application_name": "insight-flow-app"  # Identify application in connection logs
}

# Handle SSL for pg8000
if "pg8000" in database_url:
    # Remove query parameters that cause issues with pg8000 (like sslmode)
    if "?" in database_url:
        database_url = database_url.split("?")[0]
    
    # Create SSL context for Neon
    ssl_context = ssl.create_default_context()
    connect_args["ssl_context"] = ssl_context

# Log database connection details for debugging
db_logger = logging.getLogger("database")
db_logger.info("="*50)
db_logger.info("DATABASE CONFIGURATION")
db_logger.info(f"DATABASE_URL: {database_url}")
db_logger.info("="*50)

# Create engine with improved connection settings for better reliability
engine = create_engine(
    database_url,
    pool_pre_ping=True,       # Validate connections before use
    pool_recycle=300,         # Recycle connections every 5 minutes
    pool_size=int(os.getenv("DB_POOL_SIZE", "20")),             # Configurable pool size
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),       # Configurable max overflow
    pool_timeout=30,          # Timeout after 30 seconds waiting for connection
    connect_args=connect_args
)

from sqlalchemy import event
import time

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log when a connection is retrieved from the pool"""
    connection_record.info['checkout_start'] = time.time()
    # db_logger.debug("Connection checked out from pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log when a connection is returned to the pool"""
    if 'checkout_start' in connection_record.info:
        duration = time.time() - connection_record.info['checkout_start']
        # Log only if duration is significant (> 1s) to avoid noise
        if duration > 1.0:
            db_logger.warning(f"Long database connection usage: {duration:.2f}s")


# Create session factory with better isolation
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False # Prevent detaching objects after commit
)

@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    Useful for internal services or scripts ensuring session is closed.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_database():
    """
    Initialize database.
    Note: Enum creation is handled by SQLAlchemy model definitions.
    """
    pass

# Dependency to get DB session
def get_db():
    """
    Dependency to get database session with error handling and retry logic.
    """
    db_logger.debug("Creating new database session")
    
    # Simple retry logic for establishing connection
    max_retries = 3
    retry_delay = 0.5
    
    db = None
    last_error = None
    
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Test connection immediately
            db.execute(text("SELECT 1"))
            break
        except Exception as e:
            last_error = e
            db_logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if db:
                db.close()
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
    
    if not db:
        db_logger.error(f"Failed to establish database connection after {max_retries} attempts")
        raise last_error
        
    try:
        yield db
    except Exception as e:
        db_logger.error(f"Database session error: {e}")
        db.rollback()
        raise e
    finally:
        db_logger.debug("Closing database session")
        db.close()

def create_tables():
    """
    Create all database tables.
    DEPRECATED: STRICTLY DISABLED. Use Alembic migrations for schema management.
    Running this function will now raise a RuntimeError to prevent accidental schema drift.
    """
    error_msg = (
        "create_tables() is deprecated and disabled. "
        "Please use Alembic migrations to manage database schema: "
        "`alembic upgrade head`"
    )
    db_logger.error(error_msg)
    raise RuntimeError(error_msg)

# Function to drop all tables (for testing)
def drop_tables():
    """
    Drop all database tables.
    """
    Base.metadata.drop_all(bind=engine)

# Function to execute raw SQL
def execute_sql(sql_statement: str):
    """
    Execute raw SQL statement.
    """
    with engine.connect() as connection:
        result = connection.execute(text(sql_statement))
        connection.commit()
        return result