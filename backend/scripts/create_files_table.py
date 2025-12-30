import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, async_engine


async def create_tables():
    async with async_engine.begin() as conn:
        print("Creating files table...")
        await conn.run_sync(Base.metadata.create_all)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(create_tables())
