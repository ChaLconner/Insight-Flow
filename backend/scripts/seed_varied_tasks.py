"""
Seed Varied Tasks Script.

Creates projects with varying task counts for testing list virtualization.

Usage: python scripts/seed_varied_tasks.py
"""

import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from secrets import SystemRandom

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.project import MemberRole, Project, ProjectMember
from models.task import Task, TaskPriority, TaskStatus, TaskType
from models.user import User
from utils.logger import setup_logger

# Use proper logging instead of print statements
logger = setup_logger("seed_varied_tasks")
secure_random = SystemRandom()


def seed_varied_tasks():
    """Seed varied tasks for testing."""
    logger.info("Seeding varied tasks...")
    db = SessionLocal()

    try:
        # Try to find admin user first, otherwise fallback to first user
        user = db.query(User).filter(User.email == "admin@example.com").first()
        if not user:
            user = db.query(User).first()

        if not user:
            logger.warning("No users found. Please run regular seed_data.py first.")
            return

        logger.info(f"Seeding tasks for user: {user.email}")

        # Create 3 Projects with distinct task counts
        configs = [
            {"name": "Design System", "count": 4},
            {"name": "Mobile API Integration", "count": 12},
            {"name": "Q3 Marketing", "count": 7},
        ]

        created_projects = []

        for config in configs:
            # Create Project
            project_id = uuid.uuid4()
            project = Project(
                id=project_id,
                name=f"{config['name']} {secure_random.randint(100, 999)}",
                description=f"Auto-generated project with {config['count']} tasks.",
                owner_id=user.id,
                is_active=True,
            )
            db.add(project)

            # Add membership
            member = ProjectMember(
                id=uuid.uuid4(), project_id=project_id, user_id=user.id, role=MemberRole.OWNER.value
            )
            db.add(member)

            created_projects.append((project, config["count"]))

        db.commit()
        logger.info(f"Created {len(created_projects)} projects.")

        # Create Tasks
        statuses = [s.value for s in TaskStatus]
        priorities = [p.value for p in TaskPriority]
        types = [t.value for t in TaskType]

        for project, count in created_projects:
            logger.info(f"Adding {count} tasks to '{project.name}'...")
            for i in range(count):
                task = Task(
                    id=uuid.uuid4(),
                    title=f"Task {i + 1} - {project.name}",
                    description="Generated task for testing list virtualization and counts.",
                    status=secure_random.choice(statuses),
                    priority=secure_random.choice(priorities),
                    type=secure_random.choice(types),
                    project_id=project.id,
                    created_by=user.id,
                    assignee_id=user.id,
                    due_date=datetime.now(UTC) + timedelta(days=secure_random.randint(-10, 30)),
                )
                db.add(task)

        db.commit()
        logger.info("Done! Validated task counts.")

    except Exception as e:
        logger.exception(f"Error seeding varied tasks: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_varied_tasks()
