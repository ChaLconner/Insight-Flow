import asyncio
import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import select

# Add the backend directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
from models.project import MemberRole, Project, ProjectMember
from models.task import Task, TaskPriority, TaskStatus
from models.task_history import ActivityType, TaskHistory
from models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


async def seed_data():
    session = AsyncSessionLocal()
    try:
        print("Seeding data...")

        # 1. Create Users
        users_data = [
            {"email": "admin@example.com", "name": "Admin User", "role": "admin"},
            {"email": "alice@example.com", "name": "Alice Johnson", "role": "user"},
            {"email": "bob@example.com", "name": "Bob Smith", "role": "user"},
            {"email": "charlie@example.com", "name": "Charlie Brown", "role": "user"},
            {"email": "diana@example.com", "name": "Diana Prince", "role": "user"},
        ]

        created_users = []
        for u_data in users_data:
            result = await session.execute(select(User).filter(User.email == u_data["email"]))
            existing_user = result.scalars().first()

            if not existing_user:
                user = User(
                    id=uuid.uuid4(),
                    email=u_data["email"],
                    name=u_data["name"],
                    username=u_data["email"].split("@")[0],
                    hashed_password=get_password_hash("password123"),
                    is_active=True,
                    role=u_data["role"],
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                session.add(user)
                created_users.append(user)
            else:
                created_users.append(existing_user)

        await session.commit()

        # Reload users to ensure we have IDs and attached state
        # (Though we appended objects, some might be detached if we didn't refresh)
        # Simple string-based lookup for the next steps
        users_map = {u.email: u for u in created_users}

        # 2. Create Projects
        projects_data = [
            {"name": "Frontend Redesign", "desc": "Modernizing the UI/UX", "owner_email": "alice@example.com"},
            {"name": "API Optimization", "desc": "Improving backend performance", "owner_email": "bob@example.com"},
            {"name": "Mobile App V2", "desc": "New features for iOS/Android", "owner_email": "charlie@example.com"},
        ]

        # Ensure we have owners available
        # Note: index mapping in original was fragile, using email map now

        created_projects = []
        for p_data in projects_data:
            owner = users_map.get(p_data["owner_email"])
            if not owner:
                print(f"Skipping project {p_data['name']} - owner not found")
                continue

            result = await session.execute(select(Project).filter(Project.name == p_data["name"]))
            existing_project = result.scalars().first()

            if not existing_project:
                project = Project(
                    id=uuid.uuid4(),
                    name=p_data["name"],
                    description=p_data["desc"],
                    owner_id=owner.id,
                    is_active=True,
                    created_at=datetime.now(UTC) - timedelta(days=90),
                    updated_at=datetime.now(UTC),
                )
                session.add(project)
                created_projects.append(project)

                # Add owner as member
                pm_owner = ProjectMember(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    user_id=owner.id,
                    role=MemberRole.OWNER.value,
                    joined_at=datetime.now(UTC) - timedelta(days=90),
                )
                session.add(pm_owner)

                # Add random members
                for u in created_users:
                    if u.id != owner.id and random.random() > 0.4:
                        pm = ProjectMember(
                            id=uuid.uuid4(),
                            project_id=project.id,
                            user_id=u.id,
                            role=MemberRole.MEMBER.value,
                            joined_at=datetime.now(UTC) - timedelta(days=random.randint(10, 80)),
                        )
                        session.add(pm)
            else:
                created_projects.append(existing_project)

        await session.commit()

        # 3. Add ALL existing users to the new projects (if configured to do so)
        # Original script logic: add all users to created projects if not present

        # Re-fetch all users to be safe
        res_users = await session.execute(select(User))
        all_users = res_users.scalars().all()

        for project in created_projects:
            res_members = await session.execute(
                select(ProjectMember).filter(ProjectMember.project_id == project.id)
            )
            current_members = res_members.scalars().all()
            current_member_ids = {m.user_id for m in current_members}

            for user in all_users:
                if user.id not in current_member_ids:
                    pm = ProjectMember(
                        id=uuid.uuid4(),
                        project_id=project.id,
                        user_id=user.id,
                        role=MemberRole.MEMBER.value,
                        joined_at=datetime.now(UTC) - timedelta(days=random.randint(10, 80)),
                    )
                    session.add(pm)

        await session.commit()

        # 4. Create Tasks and History
        for project in created_projects:
            # Get members
            res_members = await session.execute(
                select(ProjectMember).filter(ProjectMember.project_id == project.id)
            )
            members = res_members.scalars().all()
            member_ids = [m.user_id for m in members]

            if not members:
                continue

            for _ in range(50):
                bg_days = random.randint(1, 90)
                created_date = datetime.now(UTC) - timedelta(days=bg_days)

                status_roll = random.random()
                if status_roll < 0.3:
                    status = TaskStatus.TODO
                elif status_roll < 0.7:
                    status = TaskStatus.IN_PROGRESS
                elif status_roll < 0.8:
                    status = TaskStatus.IN_REVIEW
                else:
                    status = TaskStatus.DONE

                creator_id = random.choice(member_ids)

                if status == TaskStatus.TODO:
                    assignee_id = random.choice(member_ids) if random.random() < 0.8 else None
                else:
                    assignee_id = random.choice(member_ids)

                task = Task(
                    id=uuid.uuid4(),
                    title=f"Task {uuid.uuid4().hex[:6]}",
                    description="Automatically generated task description.",
                    status=status,
                    priority=random.choice(list(TaskPriority)),
                    project_id=project.id,
                    created_by=creator_id,
                    assignee_id=assignee_id,
                    created_at=created_date,
                    due_date=created_date + timedelta(days=random.randint(2, 14)),
                )
                session.add(task)

                # Create history for creation
                h_create = TaskHistory(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    task_id=task.id,
                    user_id=creator_id,
                    activity_type=ActivityType.TASK_CREATED,
                    task_title=task.title,
                    description="Task created by user",
                    timestamp=created_date,
                )
                session.add(h_create)

                # If completed, add history
                if status == TaskStatus.DONE:
                    completion_days = random.randint(1, bg_days) if bg_days > 1 else 0
                    completed_date = created_date + timedelta(days=completion_days)
                    completed_date = min(completed_date, datetime.now(UTC))

                    h_complete = TaskHistory(
                        id=uuid.uuid4(),
                        project_id=project.id,
                        task_id=task.id,
                        user_id=assignee_id or creator_id,
                        activity_type=ActivityType.TASK_COMPLETED,
                        task_title=task.title,
                        description="Task completed",
                        timestamp=completed_date,
                        new_values='{"status": "done"}',
                    )
                    session.add(h_complete)

        await session.commit()
        print("Data seeded successfully!")

    except Exception as e:
        print(f"Error seeding data: {e}")
        await session.rollback()
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(seed_data())
