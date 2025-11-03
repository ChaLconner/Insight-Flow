#!/usr/bin/env python3
"""
Simple test script to verify Neon database connection
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def test_database_connection():
    """Test database connection and show basic info"""
    print("Testing Neon database connection...")
    
    # Load environment variables
    load_dotenv()
    
    # Check if DATABASE_URL is configured
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    print(f"DATABASE_URL found: {database_url[:50]}...")
    
    try:
        # Create database engine
        engine = create_engine(database_url)
        print("Database engine created successfully")
        
        # Test connection
        with engine.connect() as connection:
            print("Database connection established")
            
            # Get PostgreSQL version
            result = connection.execute(text('SELECT version()'))
            version = result.fetchone()[0]
            print(f"PostgreSQL version: {version}")
            
            # List tables
            result = connection.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result.fetchall()]
            print(f"Tables in database: {len(tables)} tables")
            
            if tables:
                print("Table list:")
                for table in tables:
                    print(f"   - {table}")
                    
                # Check if users table exists and count records
                if 'users' in tables:
                    result = connection.execute(text('SELECT COUNT(*) FROM users'))
                    user_count = result.fetchone()[0]
                    print(f"Users in database: {user_count}")
            else:
                print("No tables found - need to run migrations")
                
        return True
        
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    if success:
        print("\nDatabase connection test completed successfully!")
    else:
        print("\nDatabase connection test failed!")