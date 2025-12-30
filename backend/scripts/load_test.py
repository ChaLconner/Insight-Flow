"""
Load Testing Script using Locust.
Run with: locust -f scripts/load_test.py --host=http://localhost:8000

This script tests the API under various load conditions:
- Authentication endpoints
- Project CRUD operations
- Task management
- Dashboard queries
"""

import random
import string
from typing import ClassVar

from locust import HttpUser, between, events, task


def random_string(length: int = 8) -> str:
    """Generate a random string."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_email() -> str:
    """Generate a random email."""
    return f"loadtest_{random_string()}@example.com"


class InsightFlowUser(HttpUser):
    """
    Simulates a typical Insight-Flow user.
    Performs realistic user actions with think times.
    """

    # Wait 1-3 seconds between tasks
    wait_time = between(1, 3)

    # User state
    access_token = None
    user_id = None
    project_ids: ClassVar[list[str]] = []
    task_ids: ClassVar[list[str]] = []

    def on_start(self):
        """Called when user starts - login or register."""
        # Try to login with test account
        self.login()

    def login(self):
        """Login to get access token."""
        response = self.client.post(
            "/auth/login",
            json={"email": "loadtest@example.com", "password": "LoadTest123!"},
            catch_response=True,
        )

        if response.status_code == 200:
            response.success()
        elif response.status_code == 401:
            # User doesn't exist, try to register
            self.register()
        else:
            response.failure(f"Login failed: {response.status_code}")

    def register(self):
        """Register a new test user."""
        response = self.client.post(
            "/auth/register",
            json={
                "email": "loadtest@example.com",
                "password": "LoadTest123!",
                "full_name": "Load Test User",
            },
            catch_response=True,
        )

        if response.status_code in [200, 201]:
            response.success()
            # Login after registration
            self.login()
        else:
            response.failure(f"Registration failed: {response.status_code}")

    @task(10)
    def view_health(self):
        """Check health endpoint - lightweight."""
        self.client.get("/health")

    @task(5)
    def view_dashboard(self):
        """View dashboard stats."""
        self.client.get("/dashboard/stats")

    @task(8)
    def list_projects(self):
        """List all projects."""
        response = self.client.get("/projects")
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    self.project_ids = [p.get("id") for p in data[:10] if p.get("id")]
            except Exception:
                pass

    @task(6)
    def list_tasks(self):
        """List all tasks."""
        response = self.client.get("/tasks/")
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    self.task_ids = [t.get("id") for t in data[:10] if t.get("id")]
            except Exception:
                pass

    @task(3)
    def view_project(self):
        """View a single project."""
        if self.project_ids:
            project_id = random.choice(self.project_ids)
            self.client.get(f"/projects/{project_id}")

    @task(3)
    def view_task(self):
        """View a single task."""
        if self.task_ids:
            task_id = random.choice(self.task_ids)
            self.client.get(f"/tasks/{task_id}")

    @task(2)
    def create_project(self):
        """Create a new project."""
        response = self.client.post(
            "/projects",
            json={
                "name": f"Load Test Project {random_string()}",
                "description": "Created during load testing",
            },
        )
        if response.status_code in [200, 201]:
            try:
                data = response.json()
                if data.get("id"):
                    self.project_ids.append(data["id"])
            except Exception:
                pass

    @task(2)
    def view_analytics(self):
        """View analytics data."""
        if self.project_ids:
            project_id = random.choice(self.project_ids)
            self.client.get(f"/analytics/projects/{project_id}")

    @task(1)
    def view_metrics(self):
        """View Prometheus metrics."""
        self.client.get("/metrics")


class APIOnlyUser(HttpUser):
    """
    API-only user that hammers endpoints without authentication.
    Tests rate limiting and public endpoints.
    """

    wait_time = between(0.5, 1)

    @task(10)
    def health_check(self):
        """Rapid health checks."""
        self.client.get("/health")

    @task(5)
    def full_health_check(self):
        """Full health check."""
        self.client.get("/health/full")

    @task(3)
    def metrics(self):
        """Get metrics."""
        self.client.get("/metrics")

    @task(2)
    def db_health(self):
        """Database health check."""
        self.client.get("/health/db")


class StressTestUser(HttpUser):
    """
    High-frequency user for stress testing.
    Minimal wait times to test system limits.
    """

    wait_time = between(0.1, 0.5)

    @task
    def rapid_health(self):
        """Rapid health endpoint hits."""
        self.client.get("/health")


# Event handlers for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("=" * 60)
    print("INSIGHT-FLOW LOAD TEST STARTED")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("=" * 60)
    print("INSIGHT-FLOW LOAD TEST COMPLETED")
    print("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests."""
    if response_time > 1000:  # > 1 second
        print(f"SLOW REQUEST: {request_type} {name} - {response_time}ms")


# Configuration for different test scenarios
"""
Usage Examples:

# Basic load test (10 users)
locust -f scripts/load_test.py --host=http://localhost:8000 --users 10 --spawn-rate 1 --run-time 1m

# Moderate load test (50 users)
locust -f scripts/load_test.py --host=http://localhost:8000 --users 50 --spawn-rate 5 --run-time 5m

# Stress test (100 users)
locust -f scripts/load_test.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 10m

# Web UI mode
locust -f scripts/load_test.py --host=http://localhost:8000

# Headless with CSV output
locust -f scripts/load_test.py --host=http://localhost:8000 --users 50 --spawn-rate 5 --run-time 5m --headless --csv=results/load_test
"""
