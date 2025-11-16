import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

print(f"Checking all users in: {DATABASE_URL[:50]}...")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT id, email, name, is_active, created_at FROM users'))
        users = result.fetchall()
        
        print(f"\nTotal users: {len(users)}")
        print("\nUser list:")
        for user in users:
            print(f"ID: {user[0]}")
            print(f"Email: {user[1]}")
            print(f"Name: {user[2]}")
            print(f"Active: {user[3]}")
            print(f"Created: {user[4]}")
            print("-" * 40)
            
except Exception as e:
    print(f"Error: {e}")