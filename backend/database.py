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

# Database URL - read from environment variables for security
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create database engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(bind=engine)

# Dependency to get DB session
def get_db():
    """
    Dependency to get database session.
    """
    db = SessionLocal()
    try:
        yield db
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