import asyncio
import os
import sys

# Add the parent directory to sys.path to resolve imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from database import AsyncSessionLocal, database_url, init_database
from models.user import User


async def inspect_users():
    """Inspects all users in the database."""
    print(f"Connecting to database: {database_url.split('@')[-1]}")  # Print host only for privacy
    await init_database()

    async with AsyncSessionLocal() as session:
        print("\n--- User List ---")
        result = await session.execute(select(User))
        users = result.scalars().all()

        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Name: {user.name}")
            print(f"Is Active: {user.is_active}")
            print(f"Is Verified: {user.is_verified}")
            print(f"Role: {user.role}")
            print("-" * 20)

        print(f"\nTotal users: {len(users)}")


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(inspect_users())
    except Exception as e:
        print(f"Error: {e}")
