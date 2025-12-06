
import sys
import os
import uuid
import logging

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_database
from models.user import User
from models.project import Project, ProjectMember, MemberRole
from models.task import Task, TaskStatus
from services.task_service import TaskService
from services.project_service import ProjectService
from services.task_history_service import TaskHistoryService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reproduce_bug():
    init_database()
    db = SessionLocal()
    
    try:
        # 1. Setup Data: Create User, Project, Task
        email = f"test_user_{uuid.uuid4()}@example.com"
        user = User(email=email, name="Test User", hashed_password="hashed_password")
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created user: {user.id}")

        project = Project(name="Test Project", owner_id=user.id, description="Test Description")
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"Created project: {project.id}")
        
        # Add user as owner in members table too (TaskService checks this)
        project_member = ProjectMember(project_id=project.id, user_id=user.id, role=MemberRole.OWNER.value)
        db.add(project_member)
        db.commit()

        task = Task(
            title="Task to Delete",
            description="This task should be deleted",
            project_id=project.id,
            created_by=user.id,
            status=TaskStatus.TODO
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info(f"Created task: {task.id}")

        # 2. Try to Delete Task
        logger.info("Attempting to delete task...")
        task_service = TaskService(db)
        
        # This calls log_task_deleted -> inserts TaskHistory referencing task
        # Then deletes task.
        task_service.delete_task(task.id, user.id)
        
        logger.info("Task deleted successfully!")

    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    reproduce_bug()
