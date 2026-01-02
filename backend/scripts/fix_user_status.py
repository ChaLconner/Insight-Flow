import asyncio
import os
import sys

# Add the parent directory to sys.path to resolve imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from database import AsyncSessionLocal, init_database
from models.user import User


async def activate_all_users():
    """Sets is_active=True for all users in the database."""
    print("Initializing database connection...")
    await init_database()

    async with AsyncSessionLocal() as session:
        print("Fetching users...")
        result = await session.execute(select(User))
        users = result.scalars().all()

        updated_count = 0
        for user in users:
            if not user.is_active:
                print(f"Activating user: {user.email}")
                user.is_active = True
                updated_count += 1
            else:
                print(f"User already active: {user.email}")

        if updated_count > 0:
            await session.commit()
            print(f"\nSuccessfully activated {updated_count} users.")
        else:
            print("\nNo inactive users found.")


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(activate_all_users())
    except Exception as e:
        print(f"Error: {e}")
