"""Quick script to check database state"""
import sys
sys.path.insert(0, '.')

from database import SessionLocal
from models.user import User
from models.project import Project
from models.task import Task

db = SessionLocal()

print("=== USERS ===")
users = db.query(User).all()
for u in users:
    print(f"  {u.email} (id: {u.id})")

print("\n=== PROJECTS ===")
projects = db.query(Project).all()
for p in projects:
    print(f"  {p.name} (owner_id: {p.owner_id})")

print("\n=== TASKS COUNT ===")
task_count = db.query(Task).count()
print(f"  Total tasks: {task_count}")

# Count by project
for p in projects:
    count = db.query(Task).filter(Task.project_id == p.id).count()
    print(f"  {p.name}: {count} tasks")

db.close()
