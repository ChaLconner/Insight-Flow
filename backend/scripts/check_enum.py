import asyncio
import os
import sys

# Add parent directory to path to allow imports from backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from database import async_engine


async def check_enum():
    async with async_engine.begin() as conn:
        result = await conn.execute(text("SELECT unnest(enum_range(NULL::task_status))"))
        enum_values = [row[0] for row in result]
        print("Current enum values in database:", enum_values)


if __name__ == "__main__":
    asyncio.run(check_enum())
