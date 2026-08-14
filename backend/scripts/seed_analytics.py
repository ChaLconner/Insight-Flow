"""
Seed Analytics Data Script.

This script creates sample data for testing analytics features:
- Team members
- Projects with members
- Tasks with various statuses
- Task history for analytics tracking

Usage: python scripts/seed_analytics.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta
from secrets import SystemRandom

from sqlalchemy import select

# Add current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from seed_security import require_seed_password

from database import AsyncSessionLocal, init_database
from models.project import MemberRole, Project, ProjectMember
from models.task import Task, TaskPriority, TaskStatus
from models.task_history import ActivityType, TaskHistory
from models.user import User
from utils.auth import get_password_hash
from utils.logger import setup_logger

# Use proper logging instead of print statements
logger = setup_logger("seed_analytics")
secure_random = SystemRandom()


async def _get_or_create_team_member(db, name: str, seed_password: str) -> User:
    """Return the demo team member for a stable email address."""
    email = f"{name.lower().replace(' ', '.')}@example.com"
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if user:
        return user

    user = User(
        id=uuid.uuid4(),
        email=email,
        name=name,
        hashed_password=get_password_hash(seed_password),
        role="member",
        is_active=True,
        avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={name.replace(' ', '')}",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"Created user: {name}")
    return user


async def _get_or_create_analytics_project(
    db, name: str, admin_user: User, team_members: list[User]
):
    """Return a demo project and create its random member links when new."""
    result = await db.execute(select(Project).filter(Project.name == name))
    project = result.scalars().first()
    if project:
        return project

    project = Project(
        id=uuid.uuid4(),
        name=name,
        description=f"Analytics demo project: {name}",
        owner_id=admin_user.id,
        is_active=True,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    logger.info(f"Created project: {name}")

    members_to_add = secure_random.sample(
        team_members, k=secure_random.randint(2, len(team_members))
    )
    for member in members_to_add:
        if member.id != project.owner_id:
            db.add(
                ProjectMember(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    user_id=member.id,
                    role=MemberRole.MEMBER.value,
                )
            )
    await db.commit()
    return project


def _seed_project_tasks(
    db,
    project: Project,
    team_members: list[User],
    start_date: datetime,
    end_date: datetime,
) -> None:
    """Generate analytics tasks and their creation/status history for one project."""
    for _ in range(secure_random.randint(20, 40)):
        created_at = start_date + timedelta(days=secure_random.randint(0, 50))
        assignee = secure_random.choice(team_members)
        creator = secure_random.choice(team_members)
        status = secure_random.choice(list(TaskStatus))
        priority = secure_random.choice(list(TaskPriority))
        task = Task(
            id=uuid.uuid4(),
            title=f"Task {uuid.uuid4().hex[:8]}",
            description="Generated task for analytics testing",
            status=status,
            priority=priority,
            project_id=project.id,
            created_by=creator.id,
            assignee_id=assignee.id,
            due_date=created_at + timedelta(days=secure_random.randint(2, 14)),
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(task)
        db.add(
            TaskHistory(
                id=uuid.uuid4(),
                activity_type=ActivityType.TASK_CREATED,
                project_id=project.id,
                task_id=task.id,
                user_id=creator.id,
                task_title=task.title,
                description=f"Created task: {task.title}",
                timestamp=created_at,
            )
        )

        if status == TaskStatus.DONE:
            completed_at = min(created_at + timedelta(days=secure_random.randint(1, 10)), end_date)
            task.updated_at = completed_at
            db.add(
                TaskHistory(
                    id=uuid.uuid4(),
                    activity_type=ActivityType.TASK_COMPLETED,
                    project_id=project.id,
                    task_id=task.id,
                    user_id=assignee.id,
                    task_title=task.title,
                    description=f"Completed task: {task.title}",
                    timestamp=completed_at,
                    new_values='{"status": "done"}',
                )
            )
        elif status == TaskStatus.IN_PROGRESS:
            task.updated_at = created_at + timedelta(days=secure_random.randint(1, 5))


async def seed_analytics_data():
    """Seed the database with analytics test data."""
    logger.info("Starting analytics data seeding...")
    seed_password = require_seed_password()

    # Initialize database
    await init_database()

    db = AsyncSessionLocal()

    try:
        # 1. Create Team Members
        logger.info("Creating team members...")
        team_members = []
        member_names = [
            "Sarah Chen",
            "Mike Ross",
            "Alex Morgan",
            "John Doe",
            "Emily Blunt",
            "David Kim",
        ]

        for name in member_names:
            team_members.append(await _get_or_create_team_member(db, name, seed_password))

        # Get admin user
        result = await db.execute(select(User).filter(User.email == "admin@example.com"))
        admin_user = result.scalars().first()
        if not admin_user:
            logger.warning(
                "Admin user not found, please run seed_data.py first or create admin user."
            )
            return

        team_members.append(admin_user)

        # 2. Create Projects
        logger.info("Creating analytics projects...")
        project_names = [
            "Q4 Financial Report",
            "Customer Portal V2",
            "Internal Tools Migration",
            "AI Integration Alpha",
        ]
        projects = []

        for p_name in project_names:
            projects.append(
                await _get_or_create_analytics_project(db, p_name, admin_user, team_members)
            )

        # 3. Create Tasks and History
        logger.info("Generating tasks and history...")

        # Time range: Past 60 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)

        for project in projects:
            _seed_project_tasks(db, project, team_members, start_date, end_date)

        await db.commit()
        logger.info("Analytics data seeding completed successfully!")

    except Exception as e:
        # Use proper logging for errors instead of traceback.print_exc()
        logger.exception(f"An error occurred during seeding: {e}", exc_info=True)
        await db.rollback()
        raise
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(seed_analytics_data())
