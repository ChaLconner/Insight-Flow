import sys
import os

# Add parent directory to path to allow imports from backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session, joinedload
from database import SessionLocal, engine
from models.project import ProjectMember, Project, MemberRole
from models.user import User

def inspect_project_members():
    db = SessionLocal()
    try:
        members = db.query(ProjectMember).options(
            joinedload(ProjectMember.user),
            joinedload(ProjectMember.project)
        ).all()
        
        print("\n=== Project Members Inspection ===")
        print(f"Total Memberships: {len(members)}")
        
        projects = {}
        
        for member in members:
            p_name = member.project.name if member.project else "Unknown Project"
            u_name = member.user.name if member.user else "Unknown User"
            
            if p_name not in projects:
                projects[p_name] = []
            
            projects[p_name].append({
                "user": u_name,
                "email": member.user.email if member.user else "No Email",
                "role": member.role,
                "project_id": str(member.project_id),
                "user_id": str(member.user_id)
            })
            
        for project_name, members_list in projects.items():
            print(f"\nProject: {project_name}")
            print("-" * 50)
            print(f"{'User':<20} | {'Email':<25} | {'Role':<10}")
            print("-" * 50)
            for m in members_list:
                print(f"{m['user']:<20} | {m['email']:<25} | {m['role']:<10}")

    finally:
        db.close()

if __name__ == "__main__":
    inspect_project_members()
