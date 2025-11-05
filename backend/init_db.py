"""
Initialize database tables for Insight-Flow application.
"""
from database import create_tables

if __name__ == "__main__":
    print("Creating database tables...")
    create_tables()
    print("Database tables created successfully!")