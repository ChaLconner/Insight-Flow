"""Add test@example.com as member to all analytics projects"""
import sys
sys.path.insert(0, '.')

from database import SessionLocal
from models.user import User
from models.project import Project, ProjectMember, MemberRole
import uuid

db = SessionLocal()

# Find test user
test_user = db.query(User).filter(User.email == "test@example.com").first()

if not test_user:
    print("test@example.com not found!")
    exit(1)

print(f"Found test user: {test_user.email} (id: {test_user.id})")

# Get analytics projects
analytics_projects = ["Q4 Financial Report", "Customer Portal V2", "Internal Tools Migration", "AI Integration Alpha"]

for project_name in analytics_projects:
    project = db.query(Project).filter(Project.name == project_name).first()
    if project:
        # Check if already a member
        existing = db.query(ProjectMember).filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == test_user.id
        ).first()
        
        if not existing:
            pm = ProjectMember(
                id=uuid.uuid4(),
                project_id=project.id,
                user_id=test_user.id,
                role=MemberRole.MEMBER.value
            )
            db.add(pm)
            print(f"Added {test_user.email} to project: {project_name}")
        else:
            print(f"Already a member of: {project_name}")

db.commit()
print("\nDone! test@example.com now has access to analytics projects.")
db.close()
