import os
import sys
from datetime import datetime, timedelta, timezone
import uuid

# Add current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_database
from models.user import User
from models.project import Project, ProjectMember, MemberRole
from models.task import Task, TaskStatus
from utils.auth import get_password_hash

def seed_data():
    print("Starting database seeding...")
    
    # Initialize database (create enums, etc.)
    init_database()
    
    db = SessionLocal()
    
    try:
        # Check if users exist
        default_user = db.query(User).filter(User.email == "admin@example.com").first()
        
        if not default_user:
            print("Creating default user...")
            # Create default user
            default_user = User(
                id=uuid.uuid4(),
                email="admin@example.com",
                name="Admin User",
                hashed_password=get_password_hash(os.getenv("ADMIN_PASSWORD", "password123")),
                role="admin",
                is_active=True,
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=admin"
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            print(f"User created: {default_user.email}")
        else:
            print("Default user already exists.")

        print("Creating projects...")
        # Create projects
        projects_data = [
            {
                "name": "Website Redesign",
                "description": "Redesigning the corporate website with modern technologies.",
                "color": "#3b82f6"
            },
            {
                "name": "Mobile App Development",
                "description": "Developing a cross-platform mobile application for customers.",
                "color": "#8b5cf6"
            },
            {
                "name": "Marketing Campaign",
                "description": "Q4 Marketing campaign planning and execution.",
                "color": "#ec4899"
            }
        ]

        created_projects = []
        for p_data in projects_data:
            project = Project(
                id=uuid.uuid4(),
                name=p_data["name"],
                description=p_data["description"],
                owner_id=default_user.id,
                is_active=True
            )
            db.add(project)
            created_projects.append(project)
            
            # Add user as owner member
            member = ProjectMember(
                id=uuid.uuid4(),
                project_id=project.id,
                user_id=default_user.id,
                role=MemberRole.OWNER.value
            )
            db.add(member)
        
        db.commit()
        print(f"Created {len(created_projects)} projects.")

        # Create tasks for created projects
        print("Checking for projects without tasks...")
        all_projects = db.query(Project).all()
        
        for project in all_projects:
            existing_tasks = db.query(Task).filter(Task.project_id == project.id).count()
            if existing_tasks == 0:
                print(f"Adding tasks to project: {project.name}")
                project_tasks = [
                    {
                        "title": "Project Kickoff",
                        "description": "Initial meeting to discuss project goals and timeline.",
                        "status": TaskStatus.DONE.value,
                        "due_date": datetime.now(timezone.utc) - timedelta(days=2)
                    },
                    {
                        "title": "Requirements Gathering",
                        "description": "Collect and document detailed requirements.",
                        "status": TaskStatus.IN_PROGRESS.value,
                        "due_date": datetime.now(timezone.utc) + timedelta(days=5)
                    },
                    {
                        "title": "Design Phase",
                        "description": "Create UI/UX designs and prototypes.",
                        "status": TaskStatus.TODO.value,
                        "due_date": datetime.now(timezone.utc) + timedelta(days=10)
                    },
                    {
                        "title": "Implementation",
                        "description": "Start development based on approved designs.",
                        "status": TaskStatus.TODO.value,
                        "due_date": datetime.now(timezone.utc) + timedelta(days=20)
                    }
                ]

                for task_data in project_tasks:
                    task = Task(
                        id=uuid.uuid4(),
                        title=task_data["title"],
                        description=task_data["description"],
                        status=task_data["status"],
                        project_id=project.id,
                        created_by=default_user.id,
                        assignee_id=default_user.id,
                        due_date=task_data["due_date"]
                    )
                    db.add(task)
        
        db.commit()
        print("Tasks created successfully for all projects.")
        print("Seeding completed successfully!")

    except Exception as e:
        print(f"An error occurred during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
