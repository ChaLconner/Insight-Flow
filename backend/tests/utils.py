"""
Test utilities and helper functions.
"""
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
from fastapi.testclient import TestClient

class TestDataManager:
    """Manage test data creation and cleanup."""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.created_users = []
        self.created_projects = []
        self.created_tasks = []
    
    def create_test_user(self, email: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a test user."""
        from services.user_service import UserService
        from schemas.user import UserCreate
        
        if not email:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        if not name:
            name = f"Test User {uuid.uuid4().hex[:8]}"
        
        user_service = UserService(self.db_session)
        user_data = UserCreate(
            email=email,
            name=name,
            password="testpassword123"
        )
        
        user = user_service.create_user(user_data)
        self.created_users.append(user)
        return user
    
    def create_test_project(self, owner_id: uuid.UUID, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a test project."""
        from services.project_service import ProjectService
        from schemas.project import ProjectCreate
        
        if not name:
            name = f"Test Project {uuid.uuid4().hex[:8]}"
        
        project_service = ProjectService(self.db_session)
        project_data = ProjectCreate(
            name=name,
            description=f"Test project description {uuid.uuid4().hex[:8]}"
        )
        
        project = project_service.create_project(project_data, owner_id)
        self.created_projects.append(project)
        return project
    
    def create_test_task(self, project_id: uuid.UUID, creator_id: uuid.UUID, 
                       title: Optional[str] = None) -> Dict[str, Any]:
        """Create a test task."""
        from services.task_service import TaskService
        from schemas.task import TaskCreate
        
        if not title:
            title = f"Test Task {uuid.uuid4().hex[:8]}"
        
        task_service = TaskService(self.db_session)
        task_data = TaskCreate(
            title=title,
            description=f"Test task description {uuid.uuid4().hex[:8]}",
            project_id=project_id,
            due_date=datetime.utcnow() + timedelta(days=7)
        )
        
        task = task_service.create_task(task_data, creator_id)
        self.created_tasks.append(task)
        return task
    
    def add_project_member(self, project_id: uuid.UUID, user_id: uuid.UUID, 
                        role: str = "member") -> Dict[str, Any]:
        """Add a member to a test project."""
        from services.project_service import ProjectService
        from schemas.project import ProjectMemberCreate
        
        project_service = ProjectService(self.db_session)
        member_data = ProjectMemberCreate(
            user_id=user_id,
            role=role
        )
        
        return project_service.add_project_member(project_id, member_data, user_id)
    
    def cleanup(self):
        """Clean up created test data."""
        # Note: This would need proper cascade deletion setup
        # For now, just clear the tracking lists
        self.created_users.clear()
        self.created_projects.clear()
        self.created_tasks.clear()

class AuthHelper:
    """Helper for authentication in tests."""
    
    @staticmethod
    def create_test_token(user_id: str, secret_key: str = "test_secret") -> str:
        """Create a test JWT token."""
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")
    
    @staticmethod
    def create_expired_token(user_id: str, secret_key: str = "test_secret") -> str:
        """Create an expired JWT token."""
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2),
            "type": "access"
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")
    
    @staticmethod
    def create_headers(token: str) -> Dict[str, str]:
        """Create authorization headers."""
        return {"Authorization": f"Bearer {token}"}

class ResponseValidator:
    """Helper for validating API responses."""
    
    @staticmethod
    def assert_success_response(response, expected_status: int = 200):
        """Assert successful response."""
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        
        if response.status_code != 204:  # No content
            assert "application/json" in response.headers.get("content-type", "")
    
    @staticmethod
    def assert_error_response(response, expected_status: int, expected_detail: Optional[str] = None):
        """Assert error response."""
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        
        if expected_detail:
            assert expected_detail in response.json().get("detail", "")
    
    @staticmethod
    def assert_pagination_structure(data: Dict[str, Any]):
        """Assert pagination response structure."""
        required_fields = ["items", "total", "page", "limit", "pages"]
        for field in required_fields:
            assert field in data, f"Missing pagination field: {field}"
        
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["pages"], int)
    
    @staticmethod
    def assert_user_structure(data: Dict[str, Any]):
        """Assert user response structure."""
        required_fields = ["id", "email", "name", "is_active", "created_at", "updated_at"]
        for field in required_fields:
            assert field in data, f"Missing user field: {field}"
        
        assert isinstance(data["id"], str)
        assert isinstance(data["email"], str)
        assert isinstance(data["name"], str)
        assert isinstance(data["is_active"], bool)
    
    @staticmethod
    def assert_project_structure(data: Dict[str, Any]):
        """Assert project response structure."""
        required_fields = ["id", "name", "description", "owner_id", "is_active", "created_at", "updated_at"]
        for field in required_fields:
            assert field in data, f"Missing project field: {field}"
        
        assert isinstance(data["id"], str)
        assert isinstance(data["name"], str)
        assert isinstance(data["description"], str)
        assert isinstance(data["owner_id"], str)
        assert isinstance(data["is_active"], bool)
    
    @staticmethod
    def assert_task_structure(data: Dict[str, Any]):
        """Assert task response structure."""
        required_fields = ["id", "title", "description", "status", "project_id", "created_at", "updated_at"]
        for field in required_fields:
            assert field in data, f"Missing task field: {field}"
        
        assert isinstance(data["id"], str)
        assert isinstance(data["title"], str)
        assert isinstance(data["description"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["project_id"], str)

class DatabaseHelper:
    """Helper for database operations in tests."""
    
    @staticmethod
    def count_users(db_session) -> int:
        """Count users in database."""
        from models.user import User
        return db_session.query(User).count()
    
    @staticmethod
    def count_projects(db_session) -> int:
        """Count projects in database."""
        from models.project import Project
        return db_session.query(Project).count()
    
    @staticmethod
    def count_tasks(db_session) -> int:
        """Count tasks in database."""
        from models.task import Task
        return db_session.query(Task).count()
    
    @staticmethod
    def get_user_by_email(db_session, email: str):
        """Get user by email."""
        from models.user import User
        return db_session.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_project_by_name(db_session, name: str):
        """Get project by name."""
        from models.project import Project
        return db_session.query(Project).filter(Project.name == name).first()

class PerformanceHelper:
    """Helper for performance testing."""
    
    @staticmethod
    def measure_response_time(func, *args, **kwargs) -> tuple:
        """Measure response time of a function."""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    @staticmethod
    def assert_response_time(response_time: float, max_time: float):
        """Assert response time is within limits."""
        assert response_time < max_time, f"Response time {response_time}s exceeds max {max_time}s"
    
    @staticmethod
    def run_concurrent_requests(func, num_requests: int, *args, **kwargs) -> list:
        """Run multiple concurrent requests."""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker():
            try:
                result = func(*args, **kwargs)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for _ in range(num_requests):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        return results, errors

class TestDataGenerator:
    """Generate test data for various scenarios."""
    
    @staticmethod
    def generate_user_data(override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate user test data."""
        data = {
            "email": f"user_{uuid.uuid4().hex[:8]}@example.com",
            "name": f"User {uuid.uuid4().hex[:8]}",
            "password": "testpassword123"
        }
        
        if override:
            data.update(override)
        
        return data
    
    @staticmethod
    def generate_project_data(override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate project test data."""
        data = {
            "name": f"Project {uuid.uuid4().hex[:8]}",
            "description": f"Description {uuid.uuid4().hex[:16]}"
        }
        
        if override:
            data.update(override)
        
        return data
    
    @staticmethod
    def generate_task_data(override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate task test data."""
        data = {
            "title": f"Task {uuid.uuid4().hex[:8]}",
            "description": f"Description {uuid.uuid4().hex[:16]}",
            "project_id": str(uuid.uuid4()),
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
        }
        
        if override:
            data.update(override)
        
        return data
    
    @staticmethod
    def generate_invalid_data(data_type: str) -> Dict[str, Any]:
        """Generate invalid test data for validation testing."""
        if data_type == "user":
            return {
                "email": "invalid-email",
                "name": "",
                "password": "123"  # Too short
            }
        elif data_type == "project":
            return {
                "name": "",  # Empty name
                "description": "a" * 1000  # Too long
            }
        elif data_type == "task":
            return {
                "title": "",  # Empty title
                "project_id": "invalid-uuid",
                "due_date": "invalid-date"
            }
        else:
            return {}

class MockHelper:
    """Helper for mocking external services."""
    
    @staticmethod
    def mock_google_oauth():
        """Mock Google OAuth response."""
        return {
            "sub": "google_user_id",
            "email": "googleuser@example.com",
            "name": "Google User",
            "picture": "https://lh3.googleusercontent.com/avatar.jpg"
        }
    
    @staticmethod
    def mock_email_service():
        """Mock email service response."""
        return {
            "message_id": "msg_123456",
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def mock_file_upload():
        """Mock file upload response."""
        return {
            "filename": "test_file.jpg",
            "url": "https://example.com/files/test_file.jpg",
            "size": 1024,
            "content_type": "image/jpeg"
        }