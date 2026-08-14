"""
Seed Varied Tasks Script.

Creates projects with varying task counts for testing list virtualization.

Usage: python scripts/seed_varied_tasks.py
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from secrets import SystemRandom

from sqlalchemy import select

# Add the backend directory to the import path before loading application modules.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seed_security import require_seed_password

from database import AsyncSessionLocal
from models.project import MemberRole, Project, ProjectMember
from models.task import Task, TaskPriority, TaskStatus, TaskType
from models.user import User
from utils.logger import setup_logger

# Use proper logging instead of print statements
logger = setup_logger("seed_varied_tasks")
secure_random = SystemRandom()


async def seed_varied_tasks():
    """Seed varied tasks for testing."""
    require_seed_password()
    logger.info("Seeding varied tasks...")
    async with AsyncSessionLocal() as db:
        try:
            # Try to find admin user first, otherwise fallback to first user.
            result = await db.execute(select(User).filter(User.email == "admin@example.com"))
            user = result.scalars().first()
            if not user:
                result = await db.execute(select(User))
                user = result.scalars().first()

            if not user:
                logger.warning("No users found. Please run regular seed_data.py first.")
                return

            logger.info(f"Seeding tasks for user: {user.email}")

            # Create 3 Projects with distinct task counts.
            configs = [
                {"name": "Design System", "count": 4},
                {"name": "Mobile API Integration", "count": 12},
                {"name": "Q3 Marketing", "count": 7},
            ]

            created_projects = []

            for config in configs:
                project_id = uuid.uuid4()
                project = Project(
                    id=project_id,
                    name=f"{config['name']} {secure_random.randint(100, 999)}",
                    description=f"Auto-generated project with {config['count']} tasks.",
                    owner_id=user.id,
                    is_active=True,
                )
                db.add(project)

                db.add(
                    ProjectMember(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        user_id=user.id,
                        role=MemberRole.OWNER.value,
                    )
                )
                created_projects.append((project, config["count"]))

            await db.commit()
            logger.info(f"Created {len(created_projects)} projects.")

            statuses = [s.value for s in TaskStatus]
            priorities = [p.value for p in TaskPriority]
            types = [t.value for t in TaskType]

            for project, count in created_projects:
                logger.info(f"Adding {count} tasks to '{project.name}'...")
                for i in range(count):
                    db.add(
                        Task(
                            id=uuid.uuid4(),
                            title=f"Task {i + 1} - {project.name}",
                            description="Generated task for testing list virtualization and counts.",
                            status=secure_random.choice(statuses),
                            priority=secure_random.choice(priorities),
                            type=secure_random.choice(types),
                            project_id=project.id,
                            created_by=user.id,
                            assignee_id=user.id,
                            due_date=datetime.now(UTC)
                            + timedelta(days=secure_random.randint(-10, 30)),
                        )
                    )

            await db.commit()
            logger.info("Done! Validated task counts.")

        except Exception as e:
            logger.exception(f"Error seeding varied tasks: {e}", exc_info=True)
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_varied_tasks())
