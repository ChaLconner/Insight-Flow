
import sys
import os
import uuid
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from passlib.context import CryptContext

# Add the backend directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, get_db, engine
from models.user import User
from models.project import Project, ProjectMember, MemberRole
from models.task import Task, TaskStatus, TaskPriority
from models.task_history import TaskHistory, ActivityType

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed_data():
    session = Session(engine)
    try:
        print("Seeding data...")
        
        # 1. Create Users
        users_data = [
            {"email": "admin@example.com", "name": "Admin User", "role": "admin"},
            {"email": "alice@example.com", "name": "Alice Johnson", "role": "user"},
            {"email": "bob@example.com", "name": "Bob Smith", "role": "user"},
            {"email": "charlie@example.com", "name": "Charlie Brown", "role": "user"},
            {"email": "diana@example.com", "name": "Diana Prince", "role": "user"}
        ]
        
        created_users = []
        for u_data in users_data:
            existing_user = session.query(User).filter(User.email == u_data["email"]).first()
            if not existing_user:
                user = User(
                    id=uuid.uuid4(),
                    email=u_data["email"],
                    name=u_data["name"],
                    username=u_data["email"].split('@')[0],
                    hashed_password=get_password_hash("password123"),
                    is_active=True,
                    role=u_data["role"],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(user)
                created_users.append(user)
            else:
                created_users.append(existing_user)
        
        session.flush() # Commit users to get IDs
        
        # 2. Create Projects
        projects_data = [
            {"name": "Frontend Redesign", "desc": "Modernizing the UI/UX", "owner_idx": 1},
            {"name": "API Optimization", "desc": "Improving backend performance", "owner_idx": 2},
            {"name": "Mobile App V2", "desc": "New features for iOS/Android", "owner_idx": 3}
        ]
        
        created_projects = []
        for p_data in projects_data:
            owner = created_users[p_data["owner_idx"]]
            
            # Check exist name
            existing_project = session.query(Project).filter(Project.name == p_data["name"]).first()
            if not existing_project:
                project = Project(
                    id=uuid.uuid4(),
                    name=p_data["name"],
                    description=p_data["desc"],
                    owner_id=owner.id,
                    is_active=True,
                    created_at=datetime.now(timezone.utc) - timedelta(days=90),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(project)
                created_projects.append(project)
                
                # Add owner as member
                pm_owner = ProjectMember(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    user_id=owner.id,
                    role=MemberRole.OWNER.value,
                    joined_at=datetime.now(timezone.utc) - timedelta(days=90)
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
                            joined_at=datetime.now(timezone.utc) - timedelta(days=random.randint(10, 80))
                        )
                        session.add(pm)
            else:
                created_projects.append(existing_project)
                
        session.flush()

        # 3. Add ALL existing users to the new projects to ensure current user sees data
        all_users = session.query(User).all()
        for project in created_projects:
            current_member_ids = [m.user_id for m in session.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()]
            
            for user in all_users:
                if user.id not in current_member_ids:
                    pm = ProjectMember(
                        id=uuid.uuid4(),
                        project_id=project.id,
                        user_id=user.id,
                        role=MemberRole.MEMBER.value,
                        joined_at=datetime.now(timezone.utc) - timedelta(days=random.randint(10, 80))
                    )
                    session.add(pm)
        
        session.flush()

        # 4. Create Tasks and History
        for project in created_projects:
            # Get members (now includes complete list)
            members = session.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()
            member_ids = [m.user_id for m in members]
            
            if not members:
                continue

            for _ in range(50): # 50 Tasks per project
                bg_days = random.randint(1, 90)
                created_date = datetime.now(timezone.utc) - timedelta(days=bg_days)
                
                status_roll = random.random()
                if status_roll < 0.3: status = TaskStatus.TODO
                elif status_roll < 0.7: status = TaskStatus.IN_PROGRESS
                elif status_roll < 0.8: status = TaskStatus.IN_REVIEW
                else: status = TaskStatus.DONE
                
                creator_id = random.choice(member_ids)
                
                # Assign 80% of TODO tasks, and 100% of others
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
                    created_at=created_date, # This assumes BaseModel allows override or we set it later
                    due_date=created_date + timedelta(days=random.randint(2, 14))
                )
                # Hack to override server_default timestamp if needed, but BaseModel usually OK if value provided
                session.add(task)
                
                # Create history for creation
                h_create = TaskHistory(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    task_id=task.id,
                    user_id=creator_id,
                    activity_type=ActivityType.TASK_CREATED,
                    task_title=task.title,
                    description=f"Task created by user",
                    timestamp=created_date
                )
                session.add(h_create)
                
                # If completed, add history
                if status == TaskStatus.DONE:
                    completion_days = random.randint(1, bg_days) if bg_days > 1 else 0
                    completed_date = created_date + timedelta(days=completion_days)
                    if completed_date > datetime.now(timezone.utc):
                        completed_date = datetime.now(timezone.utc)
                        
                    h_complete = TaskHistory(
                        id=uuid.uuid4(),
                        project_id=project.id,
                        task_id=task.id,
                        user_id=assignee_id or creator_id,
                        activity_type=ActivityType.TASK_COMPLETED,
                        task_title=task.title,
                        description=f"Task completed",
                        timestamp=completed_date,
                        new_values='{"status": "done"}'
                    )
                    session.add(h_complete)

        session.commit()
        print("Data seeded successfully!")

    except Exception as e:
        print(f"Error seeding data: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    seed_data()
