"""
Seed Demo User Script.

Creates or updates a demo user for testing purposes.

Usage: python scripts/seed_demo_user.py
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

# Add the backend directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seed_security import require_seed_password

from database import AsyncSessionLocal
from models.user import User
from utils.auth import get_password_hash
from utils.logger import setup_logger

# Use proper logging instead of print statements
logger = setup_logger("seed_demo_user")


async def seed_demo_user():
    """Create or update demo user for testing."""
    password = require_seed_password()
    session = AsyncSessionLocal()
    try:
        email = "demo@insightflow.com"

        logger.info(f"Checking for demo user: {email}")
        result = await session.execute(select(User).filter(User.email == email))
        existing_user = result.scalars().first()

        if existing_user:
            logger.info("Demo user already exists. Updating password...")
            existing_user.hashed_password = get_password_hash(password)
            existing_user.is_verified = True
            existing_user.is_active = True
            existing_user.role = "manager"
        else:
            logger.info("Creating demo user...")
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
        logger.info(f"Demo user ready! Email: {email}")
        # Security: Don't log the password, even in development
        logger.debug("Password set successfully (not logged for security)")

    except Exception as e:
        logger.exception(f"Error seeding demo user: {e}", exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(seed_demo_user())
