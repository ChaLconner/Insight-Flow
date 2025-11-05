"""
Database configuration for Insight-Flow application.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Load environment variables from .env file
load_dotenv()

# Use Neon PostgreSQL database with improved connection settings
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://neondb_owner:npg_8iH7feIFulOq@ep-divine-tree-a129b65i-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")

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

# Dependency to get DB session
def get_db():
    """
    Dependency to get database session with error handling.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Function to create all tables
def create_tables():
    """
    Create all database tables.
    """
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