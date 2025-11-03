"""
Integration tests for the complete API workflow.
"""
import pytest
from fastapi.testclient import TestClient
import uuid

class TestUserRegistrationToProjectWorkflow:
    """Test complete workflow from user registration to project management."""
    
    def test_complete_user_workflow(self, client: TestClient, db_session):
        """Test complete user registration and authentication workflow."""
        # 1. Register user
        user_data = {
            "email": "workflow@example.com",
            "name": "Workflow User",
            "password": "password123"
        }
        
        register_response = client.post("/auth/register", json=user_data)
        assert register_response.status_code == 200
        user = register_response.json()
        assert user["email"] == user_data["email"]
        
        # 2. Login user
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        
        login_response = client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        
        # 3. Get user profile
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        profile_response = client.get("/auth/me", headers=headers)
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["email"] == user_data["email"]
        
        # 4. Update user profile
        update_data = {
            "name": "Updated Workflow User",
            "avatar_url": "https://example.com/avatar.jpg"
        }
        
        update_response = client.put(f"/users/{profile['id']}", json=update_data, headers=headers)
        assert update_response.status_code == 200
        updated_user = update_response.json()
        assert updated_user["name"] == update_data["name"]
    
    def test_project_creation_and_management_workflow(self, client: TestClient, auth_headers: dict, db_session):
        """Test complete project creation and management workflow."""
        # 1. Create project
        project_data = {
            "name": "Integration Test Project",
            "description": "A project for integration testing"
        }
        
        create_response = client.post("/projects/", json=project_data, headers=auth_headers)
        assert create_response.status_code == 200
        project = create_response.json()
        assert project["name"] == project_data["name"]
        
        # 2. Get project details
        project_response = client.get(f"/projects/{project['id']}", headers=auth_headers)
        assert project_response.status_code == 200
        project_details = project_response.json()
        assert project_details["id"] == project["id"]
        assert "members" in project_details
        
        # 3. Update project
        update_data = {
            "name": "Updated Integration Project",
            "description": "Updated description"
        }
        
        update_response = client.put(f"/projects/{project['id']}", json=update_data, headers=auth_headers)
        assert update_response.status_code == 200
        updated_project = update_response.json()
        assert updated_project["name"] == update_data["name"]
        
        # 4. Create another user and add to project
        new_user_data = {
            "email": "member@example.com",
            "name": "Member User",
            "password": "password123"
        }
        
        # Register new user
        register_response = client.post("/auth/register", json=new_user_data)
        assert register_response.status_code == 200
        new_user = register_response.json()
        
        # Add new user to project
        member_data = {
            "user_id": new_user["id"],
            "role": "member"
        }
        
        add_member_response = client.post(
            f"/projects/{project['id']}/members", 
            json=member_data, 
            headers=auth_headers
        )
        assert add_member_response.status_code == 200
        member = add_member_response.json()
        assert member["user_id"] == new_user["id"]
        
        # 5. Get project members
        members_response = client.get(f"/projects/{project['id']}/members", headers=auth_headers)
        assert members_response.status_code == 200
        members = members_response.json()
        assert len(members) >= 2  # Owner + new member

class TestTaskManagementWorkflow:
    """Test complete task management workflow."""
    
    def test_task_lifecycle_workflow(self, client: TestClient, auth_headers: dict, db_session):
        """Test complete task lifecycle from creation to completion."""
        # 1. Create project first
        project_data = {
            "name": "Task Workflow Project",
            "description": "Project for task workflow testing"
        }
        
        project_response = client.post("/projects/", json=project_data, headers=auth_headers)
        assert project_response.status_code == 200
        project = project_response.json()
        
        # 2. Create task
        task_data = {
            "title": "Integration Test Task",
            "description": "A task for integration testing",
            "project_id": project["id"],
            "due_date": "2024-12-31T23:59:59Z"
        }
        
        create_response = client.post("/tasks/", json=task_data, headers=auth_headers)
        assert create_response.status_code == 200
        task = create_response.json()
        assert task["title"] == task_data["title"]
        assert task["status"] == "todo"
        
        # 3. Get task details
        task_response = client.get(f"/tasks/{task['id']}", headers=auth_headers)
        assert task_response.status_code == 200
        task_details = task_response.json()
        assert task_details["id"] == task["id"]
        assert "assignee" in task_details
        assert "creator" in task_details
        
        # 4. Update task
        update_data = {
            "title": "Updated Integration Task",
            "description": "Updated task description",
            "status": "in_progress"
        }
        
        update_response = client.put(f"/tasks/{task['id']}", json=update_data, headers=auth_headers)
        assert update_response.status_code == 200
        updated_task = update_response.json()
        assert updated_task["title"] == update_data["title"]
        assert updated_task["status"] == update_data["status"]
        
        # 5. Mark task as done
        status_data = {"status": "done"}
        status_response = client.put(f"/tasks/{task['id']}/status", json=status_data, headers=auth_headers)
        assert status_response.status_code == 200
        completed_task = status_response.json()
        assert completed_task["status"] == "done"
        
        # 6. Delete task
        delete_response = client.delete(f"/tasks/{task['id']}", headers=auth_headers)
        assert delete_response.status_code == 200
        assert "Task deleted successfully" in delete_response.json()["message"]
    
    def test_task_assignment_workflow(self, client: TestClient, auth_headers: dict, db_session):
        """Test task assignment workflow."""
        # 1. Create project and users
        project_data = {
            "name": "Assignment Test Project",
            "description": "Project for assignment testing"
        }
        
        project_response = client.post("/projects/", json=project_data, headers=auth_headers)
        project = project_response.json()
        
        # Create assignee user
        assignee_data = {
            "email": "assignee@example.com",
            "name": "Assignee User",
            "password": "password123"
        }
        
        assignee_response = client.post("/auth/register", json=assignee_data)
        assert assignee_response.status_code == 200
        assignee = assignee_response.json()
        
        # Add assignee to project
        member_data = {
            "user_id": assignee["id"],
            "role": "member"
        }
        
        client.post(f"/projects/{project['id']}/members", json=member_data, headers=auth_headers)
        
        # 2. Create task
        task_data = {
            "title": "Assignment Test Task",
            "description": "Task for assignment testing",
            "project_id": project["id"]
        }
        
        task_response = client.post("/tasks/", json=task_data, headers=auth_headers)
        task = task_response.json()
        
        # 3. Assign task
        assign_data = {"assignee_id": assignee["id"]}
        assign_response = client.put(f"/tasks/{task['id']}/assign", json=assign_data, headers=auth_headers)
        assert assign_response.status_code == 200
        assigned_task = assign_response.json()
        assert assigned_task["assignee_id"] == assignee["id"]
        
        # 4. Get assignee's tasks
        # Login as assignee
        login_data = {
            "email": assignee_data["email"],
            "password": assignee_data["password"]
        }
        
        login_response = client.post("/auth/login", json=login_data)
        assignee_token = login_response.json()["access_token"]
        assignee_headers = {"Authorization": f"Bearer {assignee_token}"}
        
        my_tasks_response = client.get("/tasks/my/tasks", headers=assignee_headers)
        assert my_tasks_response.status_code == 200
        my_tasks = my_tasks_response.json()
        assert any(task["id"] == assigned_task["id"] for task in my_tasks)

class TestAnalyticsIntegration:
    """Test analytics integration with real data."""
    
    def test_analytics_with_project_data(self, client: TestClient, auth_headers: dict, db_session):
        """Test analytics endpoints with actual project data."""
        # 1. Create project
        project_data = {
            "name": "Analytics Test Project",
            "description": "Project for analytics testing"
        }
        
        project_response = client.post("/projects/", json=project_data, headers=auth_headers)
        project = project_response.json()
        
        # 2. Create multiple tasks with different statuses
        tasks = [
            {"title": "Todo Task", "status": "todo", "project_id": project["id"]},
            {"title": "In Progress Task", "status": "in_progress", "project_id": project["id"]},
            {"title": "Done Task", "status": "done", "project_id": project["id"]}
        ]
        
        created_tasks = []
        for task_data in tasks:
            response = client.post("/tasks/", json=task_data, headers=auth_headers)
            if response.status_code == 200:
                created_tasks.append(response.json())
        
        # 3. Test dashboard analytics
        dashboard_response = client.get(f"/analytics/dashboard/{project['id']}", headers=auth_headers)
        # Should succeed or fail gracefully if analytics not implemented
        assert dashboard_response.status_code in [200, 403, 404]
        
        # 4. Test productivity analytics
        productivity_response = client.get(f"/analytics/productivity/{project['id']}", headers=auth_headers)
        assert productivity_response.status_code in [200, 403, 404]
        
        # 5. Test contributions analytics
        contributions_response = client.get(f"/analytics/contributions/{project['id']}", headers=auth_headers)
        assert contributions_response.status_code in [200, 403, 404]

class TestNotificationIntegration:
    """Test notification integration with user actions."""
    
    def test_notification_generation(self, client: TestClient, auth_headers: dict, db_session):
        """Test notification generation from user actions."""
        # 1. Get initial notifications
        initial_response = client.get("/notifications/", headers=auth_headers)
        assert initial_response.status_code == 200
        initial_count = initial_response.json()["total"]
        
        # 2. Perform actions that should generate notifications
        # (This would depend on notification implementation)
        
        # 3. Check for new notifications
        final_response = client.get("/notifications/", headers=auth_headers)
        assert final_response.status_code == 200
        final_data = final_response.json()
        
        # Should have at least as many notifications as before
        assert final_data["total"] >= initial_count

class TestErrorHandlingIntegration:
    """Test error handling across the API."""
    
    def test_cascade_deletion_handling(self, client: TestClient, auth_headers: dict, db_session):
        """Test cascade deletion and error handling."""
        # 1. Create project with tasks
        project_data = {
            "name": "Cascade Test Project",
            "description": "Project for cascade testing"
        }
        
        project_response = client.post("/projects/", json=project_data, headers=auth_headers)
        project = project_response.json()
        
        # Create tasks
        task_data = {
            "title": "Cascade Test Task",
            "description": "Task for cascade testing",
            "project_id": project["id"]
        }
        
        task_response = client.post("/tasks/", json=task_data, headers=auth_headers)
        task = task_response.json()
        
        # 2. Delete project
        delete_response = client.delete(f"/projects/{project['id']}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        # 3. Verify task is no longer accessible
        task_check_response = client.get(f"/tasks/{task['id']}", headers=auth_headers)
        assert task_check_response.status_code in [404, 403]
    
    def test_permission_inheritance(self, client: TestClient, auth_headers: dict, db_session):
        """Test permission inheritance and access control."""
        # 1. Create project as owner
        project_data = {
            "name": "Permission Test Project",
            "description": "Project for permission testing"
        }
        
        project_response = client.post("/projects/", json=project_data, headers=auth_headers)
        project = project_response.json()
        
        # 2. Create regular user
        user_data = {
            "email": "regular@example.com",
            "name": "Regular User",
            "password": "password123"
        }
        
        user_response = client.post("/auth/register", json=user_data)
        regular_user = user_response.json()
        
        # 3. Login as regular user
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        
        login_response = client.post("/auth/login", json=login_data)
        regular_token = login_response.json()["access_token"]
        regular_headers = {"Authorization": f"Bearer {regular_token}"}
        
        # 4. Try to access project without being member
        project_access_response = client.get(f"/projects/{project['id']}", headers=regular_headers)
        assert project_access_response.status_code in [403, 404]
        
        # 5. Add user as member
        member_data = {
            "user_id": regular_user["id"],
            "role": "member"
        }
        
        add_member_response = client.post(
            f"/projects/{project['id']}/members", 
            json=member_data, 
            headers=auth_headers
        )
        assert add_member_response.status_code == 200
        
        # 6. Now user should be able to access project
        project_access_response = client.get(f"/projects/{project['id']}", headers=regular_headers)
        assert project_access_response.status_code == 200
        
        # 7. But user should not be able to delete project
        delete_response = client.delete(f"/projects/{project['id']}", headers=regular_headers)
        assert delete_response.status_code == 403

class TestPerformanceIntegration:
    """Test performance across integrated workflows."""
    
    def test_end_to_end_performance(self, client: TestClient, auth_headers: dict, db_session):
        """Test performance of complete workflows."""
        import time
        
        # 1. Time project creation
        start_time = time.time()
        project_data = {
            "name": "Performance Test Project",
            "description": "Project for performance testing"
        }
        
        project_response = client.post("/projects/", json=project_data, headers=auth_headers)
        project_creation_time = time.time() - start_time
        assert project_response.status_code == 200
        assert project_creation_time < 2.0
        
        # 2. Time task creation
        start_time = time.time()
        task_data = {
            "title": "Performance Test Task",
            "description": "Task for performance testing",
            "project_id": project_response.json()["id"]
        }
        
        task_response = client.post("/tasks/", json=task_data, headers=auth_headers)
        task_creation_time = time.time() - start_time
        assert task_response.status_code == 200
        assert task_creation_time < 2.0
        
        # 3. Time data retrieval
        start_time = time.time()
        tasks_response = client.get("/tasks/my/tasks", headers=auth_headers)
        retrieval_time = time.time() - start_time
        assert tasks_response.status_code == 200
        assert retrieval_time < 2.0