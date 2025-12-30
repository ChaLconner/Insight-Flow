import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select

# Add current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import AsyncSessionLocal, init_database
from models.project import MemberRole, Project, ProjectMember
from models.task import Task, TaskPriority, TaskStatus
from models.task_history import ActivityType, TaskHistory
from models.user import User
from utils.auth import get_password_hash


async def seed_analytics_data():  # noqa: PLR0912, PLR0915
    print("Starting analytics data seeding...")

    # Initialize database
    await init_database()

    db = AsyncSessionLocal()

    try:
        # 1. Create Team Members
        print("Creating team members...")
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
            email = f"{name.lower().replace(' ', '.')}@example.com"
            result = await db.execute(select(User).filter(User.email == email))
            user = result.scalars().first()

            if not user:
                user = User(
                    id=uuid.uuid4(),
                    email=email,
                    name=name,
                    hashed_password=get_password_hash("password123"),
                    role="member",
                    is_active=True,
                    avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={name.replace(' ', '')}",
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                print(f"Created user: {name}")

            team_members.append(user)

        # Get admin user
        result = await db.execute(select(User).filter(User.email == "admin@example.com"))
        admin_user = result.scalars().first()
        if not admin_user:
            print("Admin user not found, please run seed_data.py first or create admin user.")
            return

        team_members.append(admin_user)

        # 2. Create Projects
        print("Creating analytics projects...")
        project_names = [
            "Q4 Financial Report",
            "Customer Portal V2",
            "Internal Tools Migration",
            "AI Integration Alpha",
        ]
        projects = []

        for p_name in project_names:
            result = await db.execute(select(Project).filter(Project.name == p_name))
            project = result.scalars().first()
            if not project:
                project = Project(
                    id=uuid.uuid4(),
                    name=p_name,
                    description=f"Analytics demo project: {p_name}",
                    owner_id=admin_user.id,
                    is_active=True,
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                print(f"Created project: {p_name}")

                # Add random members to project
                members_to_add = random.sample(team_members, k=random.randint(2, len(team_members)))
                for member in members_to_add:
                    if member.id != project.owner_id:
                        pm = ProjectMember(
                            id=uuid.uuid4(),
                            project_id=project.id,
                            user_id=member.id,
                            role=MemberRole.MEMBER.value,
                        )
                        db.add(pm)
                await db.commit()

            projects.append(project)

        # 3. Create Tasks and History
        print("Generating tasks and history...")

        # Time range: Past 60 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)

        for project in projects:
            # Create 20-40 tasks per project
            num_tasks = random.randint(20, 40)

            for _ in range(num_tasks):
                # Random creation date
                created_at = start_date + timedelta(days=random.randint(0, 50))

                assignee = random.choice(team_members)
                creator = random.choice(team_members)

                status = random.choice(list(TaskStatus))
                priority = random.choice(list(TaskPriority))

                task = Task(
                    id=uuid.uuid4(),
                    title=f"Task {uuid.uuid4().hex[:8]}",
                    description="Generated task for analytics testing",
                    status=status,
                    priority=priority,
                    project_id=project.id,
                    created_by=creator.id,
                    assignee_id=assignee.id,
                    due_date=created_at + timedelta(days=random.randint(2, 14)),
                    created_at=created_at,
                    updated_at=created_at,  # Initial update time
                )
                db.add(task)

                # 3.1 Log Creation History
                history_create = TaskHistory(
                    id=uuid.uuid4(),
                    activity_type=ActivityType.TASK_CREATED,
                    project_id=project.id,
                    task_id=task.id,
                    user_id=creator.id,
                    task_title=task.title,
                    description=f"Created task: {task.title}",
                    timestamp=created_at,
                )
                db.add(history_create)

                # 3.2 Simulate Completion (if done)
                if status == TaskStatus.DONE:
                    # Completion happened 1-10 days after creation
                    completed_at = created_at + timedelta(days=random.randint(1, 10))
                    completed_at = min(completed_at, end_date)

                    task.updated_at = completed_at

                    history_complete = TaskHistory(
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
                    db.add(history_complete)

                elif status == TaskStatus.IN_PROGRESS:
                    # Update happened recently
                    updated_at = created_at + timedelta(days=random.randint(1, 5))
                    task.updated_at = updated_at

        await db.commit()
        print("Analytics data seeding completed successfully!")

    except Exception as e:
        print(f"An error occurred during seeding: {e}")
        import traceback

        traceback.print_exc()
        await db.rollback()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(seed_analytics_data())
