import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime

from passlib.context import CryptContext
from sqlalchemy import select

# Add the backend directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
from models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


async def seed_demo_user():
    session = AsyncSessionLocal()
    try:
        email = "demo@insightflow.com"
        password = "demo1234"

        print(f"Checking for demo user: {email}")
        result = await session.execute(select(User).filter(User.email == email))
        existing_user = result.scalars().first()

        if existing_user:
            print("Demo user already exists. Updating password...")
            existing_user.hashed_password = get_password_hash(password)
            existing_user.is_verified = True
            existing_user.is_active = True
            existing_user.role = "manager"
        else:
            print("Creating demo user...")
            user = User(
                id=uuid.uuid4(),
                email=email,
                name="Demo User",
                username="demouser",
                hashed_password=get_password_hash(password),
                is_active=True,
                is_verified=True,
                role="manager",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user)

        await session.commit()
        print(f"Demo user ready!\nEmail: {email}\nPassword: {password}")

    except Exception as e:
        print(f"Error seeding demo user: {e}")
        await session.rollback()
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(seed_demo_user())
