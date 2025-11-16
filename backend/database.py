"""
Database configuration for Insight-Flow application.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base

# Load environment variables from .env file
load_dotenv()

# Use Neon PostgreSQL database with improved connection settings
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://neondb_owner:npg_8iH7feIFulOq@ep-divine-tree-a129b65i-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")

# Log database connection details for debugging
import logging
db_logger = logging.getLogger("database")
db_logger.info("="*50)
db_logger.info("DATABASE CONFIGURATION")
db_logger.info(f"DATABASE_URL: {SQLALCHEMY_DATABASE_URL}")
db_logger.info("="*50)

# Create engine with improved connection settings for better reliability
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=300,     # Recycle connections every 5 minutes
    pool_size=5,          # Maximum number of connections to keep
    max_overflow=10,       # Allow up to 10 additional connections beyond pool_size
    connect_args={
        "connect_timeout": 10,  # Connection timeout in seconds
        "application_name": "insight-flow-app"  # Identify application in connection logs
    }
)

# Create session factory with better isolation
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

# Function to initialize database with enum creation
def init_database():
    """
    Initialize database and create enums if they don't exist.
    Uses a more robust approach to handle enum creation across PostgreSQL versions.
    """
    with engine.connect() as conn:
        try:
            # Check if enum type already exists first
            check_enum_sql = """
            SELECT EXISTS (
                SELECT 1 FROM pg_type 
                WHERE typname = 'task_status' 
                AND typtype = 'e'
            );
            """
            result = conn.execute(text(check_enum_sql))
            enum_exists = result.scalar()
            
            if not enum_exists:
                # Create the enum type without IF NOT EXISTS
                create_enum_sql = "CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'done')"
                conn.execute(text(create_enum_sql))
                db_logger.info("task_status enum created successfully")
            else:
                db_logger.info("task_status enum already exists, skipping creation")
                
            conn.commit()
            
        except Exception as e:
            db_logger.error(f"Error creating task_status enum: {e}")
            conn.rollback()
            # Try alternative approach if the first one fails
            try:
                # Try to create enum without checking (will fail if exists, but that's ok)
                conn.execute(text("CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'done')"))
                conn.commit()
                db_logger.info("task_status enum created successfully (alternative approach)")
            except Exception as alt_e:
                db_logger.warning(f"Enum creation failed (expected if already exists): {alt_e}")
                conn.rollback()
                # If we get here, the enum likely already exists, which is fine
                db_logger.info("Assuming task_status enum already exists")

# Dependency to get DB session
def get_db():
    """
    Dependency to get database session with error handling.
    """
    db_logger.debug("Creating new database session")
    db = SessionLocal()
    try:
        # Test connection
        db.execute(text("SELECT 1"))
        db_logger.debug("Database connection test successful")
        yield db
    except Exception as e:
        db_logger.error(f"Database connection error: {e}")
        db.rollback()
        raise e
    finally:
        db_logger.debug("Closing database session")
        db.close()

# Function to create all tables
def create_tables():
    """
    Create all database tables.
    """
    # First initialize enums
    init_database()
    # Then create tables
    Base.metadata.create_all(bind=engine)

# Function to drop all tables (for testing)
def drop_tables():
    """
    Drop all database tables.
    """
    Base.metadata.drop_all(bind=engine)

# Function to execute raw SQL
def execute_sql(sql_statement):
    """
    Execute raw SQL statement.
    """
    with engine.connect() as connection:
        result = connection.execute(sql_statement)
        connection.commit()
        return result