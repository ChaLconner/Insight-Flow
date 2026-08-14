import argparse
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import timedelta

from seed_security import require_dev_token_issuance
from sqlalchemy import select

from database import AsyncSessionLocal
from models.user import User
from utils.auth import create_access_token


async def _issue_token(email: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email.strip().lower()))
        user = result.scalar_one_or_none()
        if not user:
            raise SystemExit("User not found")
        if not user.is_active or not user.is_verified:
            raise SystemExit("User must be active and verified")

        token = create_access_token(
            data={
                "sub": str(user.id),
                "sv": int(getattr(user, "session_version", 0) or 0),
            },
            expires_delta=timedelta(minutes=30),
        )
        print(token)


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a short-lived development access token.")
    parser.add_argument("--email", required=True, help="Existing development user email")
    args = parser.parse_args()
    require_dev_token_issuance()
    asyncio.run(_issue_token(args.email))


if __name__ == "__main__":
    main()
