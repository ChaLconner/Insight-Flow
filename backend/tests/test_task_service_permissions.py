"""
Unit tests for TaskService permissions and edge cases.
"""
import pytest
import uuid
from models.task import Task, TaskStatus, TaskPriority, TaskType
from models.project import Project, ProjectMember, MemberRole
from models.user import User
from services.task_service import TaskService
from services.project_service import ProjectService
from schemas.task import TaskCreate, TaskUpdate, TaskStatusUpdate

class TestTaskServicePermissions:
    """Test cases for TaskService permissions."""

    @pytest.fixture
    def setup_permission_data(self, db_session):
        """Create users with different roles and a project."""
        from utils.auth import get_password_hash
        
        # Helper to create user
        def create_user(email, name):
            user = User(
                email=email,
                hashed_password=get_password_hash("password123"),
                name=name,
                is_active=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            return user

        owner = create_user("owner@test.com", "Owner")
        admin = create_user("admin@test.com", "Admin")
        member = create_user("member@test.com", "Member")
        assignee = create_user("assignee@test.com", "Assignee")
        stranger = create_user("stranger@test.com", "Stranger")

        # Create Project (ProjectService automatically adds owner as member)
        project = Project(
            name="Permission Test Project",
            description="Testing permissions",
            owner_id=owner.id,
            is_active=True
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)
        
        # Add Owner as ProjectMember (if not done by service, but here we do manually to be safe/explicit if not using service)
        # Note: ProjectService.create_project does this, but we are creating manually.
        # So we MUST add the owner as a member with OWNER role manually here.
        db_session.add(ProjectMember(project_id=project.id, user_id=owner.id, role=MemberRole.OWNER.value))
        
        # Add Admin
        db_session.add(ProjectMember(project_id=project.id, user_id=admin.id, role=MemberRole.ADMIN.value))
        
        # Add Member
        db_session.add(ProjectMember(project_id=project.id, user_id=member.id, role=MemberRole.MEMBER.value))
        
        # Add Assignee (as member initially)
        db_session.add(ProjectMember(project_id=project.id, user_id=assignee.id, role=MemberRole.MEMBER.value))
        
        db_session.commit()

        return {
            "project": project,
            "owner": owner,
            "admin": admin,
            "member": member,
            "assignee": assignee,
            "stranger": stranger,
            "service": TaskService(db_session)
        }

    def test_update_task_permission_denied(self, db_session, setup_permission_data):
        """Test that a regular member cannot update a task they didn't create and isn't assigned to."""
        service = setup_permission_data["service"]
        project = setup_permission_data["project"]
        owner = setup_permission_data["owner"]
        member = setup_permission_data["member"]
        
        # Task created by Owner
        task = service.create_task(
            TaskCreate(title="Owner Task", project_id=project.id),
            created_by=owner.id
        )
        
        # Member tries to update
        with pytest.raises(ValueError, match="Not authorized"):
            service.update_task(
                task.id, 
                TaskUpdate(title="Hacked Title"), 
                user_id=member.id
            )

    def test_update_task_assignee_success(self, db_session, setup_permission_data):
        """Test that the assignee can update the task."""
        service = setup_permission_data["service"]
        project = setup_permission_data["project"]
        owner = setup_permission_data["owner"]
        assignee = setup_permission_data["assignee"]
        
        # Task assigned to Assignee
        task = service.create_task(
            TaskCreate(title="Assigned Task", project_id=project.id, assignee_id=assignee.id),
            created_by=owner.id
        )
        
        # Assignee updates
        updated_task = service.update_task(
            task.id,
            TaskUpdate(description="I can update this"),
            user_id=assignee.id
        )
        
        assert updated_task.description == "I can update this"

    def test_update_task_admin_success(self, db_session, setup_permission_data):
        """Test that project admin can update any task in project."""
        service = setup_permission_data["service"]
        project = setup_permission_data["project"]
        owner = setup_permission_data["owner"]
        admin = setup_permission_data["admin"]
        
        # Task created by Owner
        task = service.create_task(
            TaskCreate(title="Owner Task", project_id=project.id),
            created_by=owner.id
        )
        
        # Admin updates
        updated_task = service.update_task(
            task.id,
            TaskUpdate(priority="urgent"),
            user_id=admin.id
        )
        assert updated_task.priority == TaskPriority.URGENT

    def test_delete_task_permission_denied_for_assignee(self, db_session, setup_permission_data):
        """Test that assignee cannot delete the task (unless they are admin/creator)."""
        service = setup_permission_data["service"]
        project = setup_permission_data["project"]
        owner = setup_permission_data["owner"]
        assignee = setup_permission_data["assignee"]
        
        # Task assigned to Assignee
        task = service.create_task(
            TaskCreate(title="Assigned Task", project_id=project.id, assignee_id=assignee.id),
            created_by=owner.id
        )
        
        # Assignee tries to delete
        with pytest.raises(ValueError, match="Not authorized"):
            service.delete_task(task.id, user_id=assignee.id)

    def test_delete_task_success_for_admin(self, db_session, setup_permission_data):
        """Test that admin can delete task."""
        service = setup_permission_data["service"]
        project = setup_permission_data["project"]
        owner = setup_permission_data["owner"]
        admin = setup_permission_data["admin"]
        
        task = service.create_task(
            TaskCreate(title="Task to Delete", project_id=project.id),
            created_by=owner.id
        )
        
        assert service.delete_task(task.id, user_id=admin.id) is True

    def test_create_task_stranger_denied(self, db_session, setup_permission_data):
        """Test that a non-member cannot create a task in the project."""
        service = setup_permission_data["service"]
        project = setup_permission_data["project"]
        stranger = setup_permission_data["stranger"]
        
        # In current TaskService.create_task implementation:
        # It checks if project exists but does NOT explicitly check if created_by is a member
        # This is a potential gap or design choice. Let's Verify.
        # Reading existing code: 
        # project = self.db.query(Project).filter(Project.id == task_data.project_id).first()
        # if not project: raise ValueError("Project not found")
        # Then it just creates it.
        # Wait, usually the Router checks permissions or the Service should.
        # If the Service doesn't check, any authenticated user can create a task in any project if they know the ID.
        # This TEST looks for that vulnerability.
        
        # If this fails (i.e., stranger CAN create), we found a security bug to fix!
        # If the requirement is that we must fix it if found, I will add the check too.
        
        # Let's assume we expect it to fail (it should fail in a secure system).
        # Note: The current service implementation I read earlier did NOT seem to have a explicit check 
        # for project membership in create_task.
        # "Check if project exists and user is a member" -- explicit comment in previous read? 
        # Let's re-read the create_task method in previous turn output...
        
        # Line 53: # Check if project exists and user is a member
        # Line 54: project = self.db.query(Project).filter(Project.id == task_data.project_id).first()
        # It gets project, but I don't see the member check logic in code after that comment!
        
        # So I expect this test to fail (Pass = Stranger created task).
        # I will write the test expecting failure, and if it passes (auth error), great.
        
        # Wait, strict TDD: I write test that EXPECTS it to raise ValueError.
        # If it doesn't raise, I know I must fix the code.
        
        # Note: If I run this now and it fails, I should fix the code.
        service = setup_permission_data["service"]
        project = setup_permission_data["project"]
        stranger = setup_permission_data["stranger"]
        
        # Stranger tries to create a task in the project
        with pytest.raises(ValueError, match="Not authorized|Project not found"):
            # Note: Depending on implementation, it might say "Project not found" if filtered by user, 
            # or "Not authorized".
            # Currently TaskService check:
            # project = db.query(Project).filter(Project.id == task_data.project_id).first()
            # If this query doesn't filter by user permissions, it will find it.
            # Then we expect it to fail if we add the permission check.
            # If existing code doesn't check, existing code is insecure and this test will FAIL (showing bug).
            service.create_task(
                TaskCreate(title="Hacked Task", project_id=project.id),
                created_by=stranger.id
            )

    def test_status_update_permission(self, db_session, setup_permission_data):
        """Test that assignee can update status."""
        service = setup_permission_data["service"]
        project = setup_permission_data["project"]
        owner = setup_permission_data["owner"]
        assignee = setup_permission_data["assignee"]
        
        task = service.create_task(
            TaskCreate(title="Status Task", project_id=project.id, assignee_id=assignee.id),
            created_by=owner.id
        )
        
        service.update_task_status(
            task.id,
            TaskStatusUpdate(status="in_progress"),
            user_id=assignee.id
        )
        
        assert task.status == TaskStatus.IN_PROGRESS
