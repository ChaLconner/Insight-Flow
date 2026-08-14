import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from secrets import SystemRandom

from sqlalchemy import select

# Add the backend directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seed_security import require_seed_password

from database import AsyncSessionLocal
from models.project import MemberRole, Project, ProjectMember
from models.task import Task, TaskPriority, TaskStatus
from models.task_history import ActivityType, TaskHistory
from models.user import User
from utils.auth import get_password_hash

secure_random = SystemRandom()


async def _seed_users(session, users_data, seed_password: str):
    created_users = []
    for user_data in users_data:
        result = await session.execute(select(User).filter(User.email == user_data["email"]))
        existing_user = result.scalars().first()
        if existing_user:
            existing_user.is_verified = True
            existing_user.is_active = True
            created_users.append(existing_user)
            continue

        user = User(
            id=uuid.uuid4(),
            email=user_data["email"],
            name=user_data["name"],
            username=user_data["email"].split("@")[0],
            hashed_password=get_password_hash(seed_password),
            is_active=True,
            is_verified=True,
            role=user_data["role"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(user)
        created_users.append(user)
    await session.commit()
    return created_users


async def _seed_projects(session, users_map, created_users, projects_data):
    created_projects = []
    for project_data in projects_data:
        owner = users_map.get(project_data["owner_email"])
        if not owner:
            print(f"Skipping project {project_data['name']} - owner not found")
            continue

        result = await session.execute(select(Project).filter(Project.name == project_data["name"]))
        existing_project = result.scalars().first()
        if existing_project:
            created_projects.append(existing_project)
            continue

        project = Project(
            id=uuid.uuid4(),
            name=project_data["name"],
            description=project_data["desc"],
            owner_id=owner.id,
            is_active=True,
            created_at=datetime.now(UTC) - timedelta(days=90),
            updated_at=datetime.now(UTC),
        )
        session.add(project)
        created_projects.append(project)
        session.add(
            ProjectMember(
                id=uuid.uuid4(),
                project_id=project.id,
                user_id=owner.id,
                role=MemberRole.OWNER.value,
                joined_at=datetime.now(UTC) - timedelta(days=90),
            )
        )
        for user in created_users:
            if user.id != owner.id and secure_random.random() > 0.4:
                session.add(
                    ProjectMember(
                        id=uuid.uuid4(),
                        project_id=project.id,
                        user_id=user.id,
                        role=MemberRole.MEMBER.value,
                        joined_at=datetime.now(UTC) - timedelta(days=secure_random.randint(10, 80)),
                    )
                )
    await session.commit()
    return created_projects


async def _add_all_users_to_projects(session, created_projects):
    result = await session.execute(select(User))
    all_users = result.scalars().all()
    for project in created_projects:
        members_result = await session.execute(
            select(ProjectMember).filter(ProjectMember.project_id == project.id)
        )
        current_member_ids = {member.user_id for member in members_result.scalars().all()}
        for user in all_users:
            if user.id not in current_member_ids:
                session.add(
                    ProjectMember(
                        id=uuid.uuid4(),
                        project_id=project.id,
                        user_id=user.id,
                        role=MemberRole.MEMBER.value,
                        joined_at=datetime.now(UTC) - timedelta(days=secure_random.randint(10, 80)),
                    )
                )
    await session.commit()


def _task_status():
    status_roll = secure_random.random()
    if status_roll < 0.3:
        return TaskStatus.TODO
    if status_roll < 0.7:
        return TaskStatus.IN_PROGRESS
    if status_roll < 0.8:
        return TaskStatus.IN_REVIEW
    return TaskStatus.DONE


def _build_task(project, member_ids):
    background_days = secure_random.randint(1, 90)
    created_date = datetime.now(UTC) - timedelta(days=background_days)
    status = _task_status()
    creator_id = secure_random.choice(member_ids)
    assignee_id = (
        secure_random.choice(member_ids)
        if status != TaskStatus.TODO or secure_random.random() < 0.8
        else None
    )
    task = Task(
        id=uuid.uuid4(),
        title=f"Task {uuid.uuid4().hex[:6]}",
        description="Automatically generated task description.",
        status=status,
        priority=secure_random.choice(list(TaskPriority)),
        project_id=project.id,
        created_by=creator_id,
        assignee_id=assignee_id,
        created_at=created_date,
        due_date=created_date + timedelta(days=secure_random.randint(2, 14)),
    )
    return task, status, creator_id, assignee_id, created_date, background_days


def _add_task_history(
    session, task, status, creator_id, assignee_id, created_date, background_days
):
    session.add(
        TaskHistory(
            id=uuid.uuid4(),
            project_id=task.project_id,
            task_id=task.id,
            user_id=creator_id,
            activity_type=ActivityType.TASK_CREATED,
            task_title=task.title,
            description="Task created by user",
            timestamp=created_date,
        )
    )
    if status == TaskStatus.DONE:
        completion_days = secure_random.randint(1, background_days) if background_days > 1 else 0
        completed_date = min(created_date + timedelta(days=completion_days), datetime.now(UTC))
        session.add(
            TaskHistory(
                id=uuid.uuid4(),
                project_id=task.project_id,
                task_id=task.id,
                user_id=assignee_id or creator_id,
                activity_type=ActivityType.TASK_COMPLETED,
                task_title=task.title,
                description="Task completed",
                timestamp=completed_date,
                new_values='{"status": "done"}',
            )
        )


async def _seed_tasks(session, created_projects):
    for project in created_projects:
        members_result = await session.execute(
            select(ProjectMember).filter(ProjectMember.project_id == project.id)
        )
        member_ids = [member.user_id for member in members_result.scalars().all()]
        if not member_ids:
            continue
        for _ in range(50):
            task, status, creator_id, assignee_id, created_date, background_days = _build_task(
                project, member_ids
            )
            session.add(task)
            _add_task_history(
                session,
                task,
                status,
                creator_id,
                assignee_id,
                created_date,
                background_days,
            )
    await session.commit()


async def seed_data():
    seed_password = require_seed_password()
    session = AsyncSessionLocal()
    try:
        print("Seeding data...")

        users_data = [
            {"email": "admin@example.com", "name": "Admin User", "role": "admin"},
            {"email": "alice@example.com", "name": "Alice Johnson", "role": "user"},
            {"email": "bob@example.com", "name": "Bob Smith", "role": "user"},
            {"email": "charlie@example.com", "name": "Charlie Brown", "role": "user"},
            {"email": "diana@example.com", "name": "Diana Prince", "role": "user"},
        ]
        created_users = await _seed_users(session, users_data, seed_password)
        users_map = {u.email: u for u in created_users}

        projects_data = [
            {
                "name": "Frontend Redesign",
                "desc": "Modernizing the UI/UX",
                "owner_email": "alice@example.com",
            },
            {
                "name": "API Optimization",
                "desc": "Improving backend performance",
                "owner_email": "bob@example.com",
            },
            {
                "name": "Mobile App V2",
                "desc": "New features for iOS/Android",
                "owner_email": "charlie@example.com",
            },
        ]
        created_projects = await _seed_projects(session, users_map, created_users, projects_data)

        await _add_all_users_to_projects(session, created_projects)

        await _seed_tasks(session, created_projects)
        print("Data seeded successfully!")

    except Exception as e:
        print(f"Error seeding data: {e}")
        await session.rollback()
        raise
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(seed_data())
