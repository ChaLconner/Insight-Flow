"""
Load Testing Script using Locust.
Run with: locust -f scripts/load_test.py --host=http://localhost:8000

This script tests the API under various load conditions:
- Authentication endpoints
- Project CRUD operations
- Task management
- Dashboard queries
"""

import json
import os
import string
from http.cookies import SimpleCookie
from itertools import count
from secrets import SystemRandom

from locust import HttpUser, between, events, task
from locust.exception import StopUser

secure_random = SystemRandom()
HEALTH_ENDPOINT = "/health"
API_PREFIX = os.getenv("LOAD_TEST_API_PREFIX", "/api/v1")
ALLOW_REGISTRATION = os.getenv("LOAD_TEST_ALLOW_REGISTRATION", "false").lower() == "true"
ALLOW_MUTATIONS = os.getenv("LOAD_TEST_ALLOW_MUTATIONS", "false").lower() == "true"
LOAD_TEST_ENVIRONMENT = os.getenv("LOAD_TEST_ENVIRONMENT", "staging").lower()
ALLOW_PRODUCTION = os.getenv("LOAD_TEST_ALLOW_PRODUCTION", "false").lower() == "true"
MAX_FAILURE_RATE = float(os.getenv("LOAD_TEST_MAX_FAILURE_RATE", "1.0"))
MAX_P95_MS = float(os.getenv("LOAD_TEST_MAX_P95_MS", "2000"))
MIN_RPS = float(os.getenv("LOAD_TEST_MIN_RPS", "0"))
MIN_REQUESTS = int(os.getenv("LOAD_TEST_MIN_REQUESTS", "1"))
RUN_PUBLIC_SCENARIO = os.getenv("LOAD_TEST_RUN_PUBLIC_SCENARIO", "false").lower() == "true"
RUN_STRESS_SCENARIO = os.getenv("LOAD_TEST_RUN_STRESS_SCENARIO", "false").lower() == "true"
EXPECTED_METRICS_STATUS = int(os.getenv("LOAD_TEST_EXPECT_METRICS_STATUS", "200"))
EXPECTED_DETAILED_HEALTH_STATUS = int(os.getenv("LOAD_TEST_EXPECT_DETAILED_HEALTH_STATUS", "200"))
_LOAD_TEST_CLIENT_IPS = count(1)


def load_credentials() -> list[tuple[str, str]]:
    """Load an isolated credential pool without logging any credential values."""
    raw_users = os.getenv("LOAD_TEST_USERS", "").strip()
    if raw_users:
        try:
            parsed_users = json.loads(raw_users)
        except json.JSONDecodeError as error:
            raise RuntimeError("LOAD_TEST_USERS must be valid JSON.") from error

        if not isinstance(parsed_users, list):
            raise RuntimeError("LOAD_TEST_USERS must be a JSON array.")

        credentials: list[tuple[str, str]] = []
        for user in parsed_users:
            if not isinstance(user, dict):
                raise RuntimeError("Each LOAD_TEST_USERS entry must be an object.")
            email = user.get("email")
            password = user.get("password")
            if not isinstance(email, str) or not email.strip() or not isinstance(password, str):
                raise RuntimeError("Each LOAD_TEST_USERS entry needs email and password.")
            credentials.append((email.strip(), password))
        if credentials:
            return credentials

    email = os.getenv("LOAD_TEST_EMAIL", "").strip()
    password = os.getenv("LOAD_TEST_PASSWORD", "")
    if email and password:
        return [(email, password)]
    return []


LOAD_TEST_CREDENTIALS = load_credentials()


def profile_from_response(response):
    """Normalize direct and envelope-style /auth/me responses."""
    payload = response.json()
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    if isinstance(payload, dict) and isinstance(payload.get("user"), dict):
        return payload["user"]
    return payload


def access_token_from_response(response) -> str | None:
    """Read the access cookie without logging or exposing its value.

    Production auth cookies are Secure and therefore are intentionally not
    sent by an HTTP load-test client. The load gate runs over loopback HTTP,
    so it promotes the already-issued access token to an in-memory Bearer
    header for subsequent requests. This preserves production cookie flags
    while exercising the same server-side authentication dependency.
    """
    cookies = getattr(response, "cookies", None)
    if cookies is not None:
        token = cookies.get("access_token")
        if token:
            return str(token)

    raw_headers = getattr(response, "headers", {})
    set_cookie = raw_headers.get("set-cookie")
    if not set_cookie:
        return None

    parsed = SimpleCookie()
    parsed.load(set_cookie)
    morsel = parsed.get("access_token")
    return morsel.value if morsel is not None else None


def random_string(length: int = 8) -> str:
    """Generate a random string."""
    return "".join(secure_random.choices(string.ascii_lowercase, k=length))


def random_email() -> str:
    """Generate a random email."""
    return f"loadtest_{random_string()}@example.com"


class InsightFlowUser(HttpUser):
    """
    Simulates a typical Insight-Flow user.
    Performs realistic user actions with think times.
    """

    # Do not create failing authenticated users when a caller intentionally
    # runs only the public health/metrics scenario without credentials.
    abstract = not bool(LOAD_TEST_CREDENTIALS)
    # Wait 1-3 seconds between tasks
    wait_time = between(1, 3)

    # User state
    access_token = None
    user_id = None
    project_ids: list[str]
    task_ids: list[str]
    authenticated = False

    def on_start(self):
        """Called when user starts - login or register."""
        if not LOAD_TEST_CREDENTIALS:
            raise RuntimeError(
                "Load test requires LOAD_TEST_USERS or both LOAD_TEST_EMAIL and LOAD_TEST_PASSWORD."
            )

        self.project_ids = []
        self.task_ids = []
        self.email, self.password = secure_random.choice(LOAD_TEST_CREDENTIALS)
        # The CI server is loopback and therefore a trusted proxy. Give each
        # Locust user a distinct documentation-range client IP so per-client
        # authentication limits model separate callers instead of one shared
        # 127.0.0.1 address.
        client_ip = next(_LOAD_TEST_CLIENT_IPS) % 254 + 1
        self.client.headers.update({"X-Forwarded-For": f"198.51.100.{client_ip}"})
        if not self.login():
            raise StopUser

    def login(self):
        """Login to get access token."""
        with self.client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": self.email, "password": self.password},
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                self.access_token = access_token_from_response(response)
                if not self.access_token:
                    response.failure("Login response did not include an access token")
                    return False

                # The CI gate deliberately uses HTTP loopback while the app
                # runs with production cookie settings. Use the token only in
                # memory; never print or persist it.
                auth_headers = {"Authorization": f"Bearer {self.access_token}"}
                self.client.headers.update(auth_headers)
                if self._verify_identity(response, auth_headers):
                    response.success()
                    return True
                return False
            if response.status_code == 401 and ALLOW_REGISTRATION:
                return self.register()

            response.failure(f"Login failed: {response.status_code}")
            return False

    def _verify_identity(self, login_response, auth_headers: dict[str, str]) -> bool:
        """Verify the token against the selected account without logging it."""
        with self.client.get(
            f"{API_PREFIX}/auth/me",
            name="auth me",
            headers=auth_headers,
            catch_response=True,
        ) as identity_response:
            if identity_response.status_code != 200:
                login_response.failure(
                    f"Authenticated identity check failed: {identity_response.status_code}"
                )
                identity_response.failure("Expected authenticated /auth/me response")
                return False
            try:
                profile = profile_from_response(identity_response)
            except (TypeError, ValueError):
                login_response.failure("Authenticated identity response was not JSON")
                identity_response.failure("Expected JSON profile")
                return False

            actual_email = profile.get("email") if isinstance(profile, dict) else None
            if not isinstance(actual_email, str) or actual_email.lower() != self.email.lower():
                login_response.failure("Authenticated identity did not match the selected user")
                identity_response.failure("Authenticated identity mismatch")
                return False

            self.user_id = profile.get("id") if isinstance(profile, dict) else None
            self.authenticated = True
            identity_response.success()
            return True

    def register(self):
        """Register a new test user."""
        with self.client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": self.email,
                "password": self.password,
                "name": "Load Test User",
            },
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                # Login after registration
                return self.login()

            response.failure(f"Registration failed: {response.status_code}")
            return False

    @task(10)
    def view_health(self):
        """Check health endpoint - lightweight."""
        self.client.get(HEALTH_ENDPOINT)

    @task(5)
    def view_dashboard(self):
        """View dashboard stats."""
        self.client.get(f"{API_PREFIX}/dashboard/overview", name="dashboard overview")

    @task(8)
    def list_projects(self):
        """List all projects."""
        response = self.client.get(f"{API_PREFIX}/projects", params={"limit": 20})
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
        response = self.client.get(f"{API_PREFIX}/tasks/", params={"limit": 20})
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict):
                    items = data.get("items", [])
                    self.task_ids = [t.get("id") for t in items[:10] if t.get("id")]
            except Exception:
                pass

    @task(3)
    def view_project(self):
        """View a single project."""
        if self.project_ids:
            project_id = secure_random.choice(self.project_ids)
            self.client.get(f"{API_PREFIX}/projects/{project_id}")

    @task(3)
    def view_task(self):
        """View a single task."""
        if self.task_ids:
            task_id = secure_random.choice(self.task_ids)
            self.client.get(f"{API_PREFIX}/tasks/{task_id}")

    @task(2)
    def create_project(self):
        """Create a new project."""
        if not ALLOW_MUTATIONS:
            return
        response = self.client.post(
            f"{API_PREFIX}/projects",
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
        self.client.get(f"{API_PREFIX}/analytics/overview")

    @task(1)
    def view_metrics(self):
        """View Prometheus metrics."""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == EXPECTED_METRICS_STATUS:
                response.success()
            else:
                response.failure(
                    f"Expected metrics status {EXPECTED_METRICS_STATUS}, got {response.status_code}"
                )


class APIOnlyUser(HttpUser):
    """
    API-only user that hammers endpoints without authentication.
    Tests rate limiting and public endpoints.
    """

    abstract = not RUN_PUBLIC_SCENARIO
    wait_time = between(0.5, 1)

    @task(10)
    def health_check(self):
        """Rapid health checks."""
        with self.client.get(HEALTH_ENDPOINT, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Expected health status 200, got {response.status_code}")

    @task(5)
    def full_health_check(self):
        """Full health check."""
        with self.client.get("/health/full", catch_response=True) as response:
            if response.status_code == EXPECTED_DETAILED_HEALTH_STATUS:
                response.success()
            else:
                response.failure(
                    "Expected detailed health status "
                    f"{EXPECTED_DETAILED_HEALTH_STATUS}, got {response.status_code}"
                )

    @task(3)
    def metrics(self):
        """Get metrics."""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == EXPECTED_METRICS_STATUS:
                response.success()
            else:
                response.failure(
                    f"Expected metrics status {EXPECTED_METRICS_STATUS}, got {response.status_code}"
                )

    @task(2)
    def db_health(self):
        """Database health check."""
        with self.client.get("/health/db", catch_response=True) as response:
            if response.status_code == EXPECTED_DETAILED_HEALTH_STATUS:
                response.success()
            else:
                response.failure(
                    "Expected database health status "
                    f"{EXPECTED_DETAILED_HEALTH_STATUS}, got {response.status_code}"
                )


class StressTestUser(HttpUser):
    """
    High-frequency user for stress testing.
    Minimal wait times to test system limits.
    """

    abstract = not RUN_STRESS_SCENARIO
    wait_time = between(0.1, 0.5)

    @task
    def rapid_health(self):
        """Rapid health endpoint hits."""
        self.client.get(HEALTH_ENDPOINT)


# Event handlers for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    if LOAD_TEST_ENVIRONMENT == "production" and not ALLOW_PRODUCTION:
        raise RuntimeError(
            "Production load requires LOAD_TEST_ALLOW_PRODUCTION=true and explicit approval."
        )

    print("=" * 60)
    print("INSIGHT-FLOW LOAD TEST STARTED")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    total = environment.stats.total
    failure_rate = total.fail_ratio * 100
    p95_ms = total.get_response_time_percentile(0.95) if total.num_requests else 0
    rps = total.total_rps

    print("=" * 60)
    print("INSIGHT-FLOW LOAD TEST COMPLETED")
    print(
        f"SUMMARY requests={total.num_requests} failures={total.num_failures} "
        f"failure_rate={failure_rate:.2f}% p95_ms={p95_ms:.0f} rps={rps:.2f}"
    )
    print("=" * 60)

    failures = []
    if total.num_requests < MIN_REQUESTS:
        failures.append(f"requests {total.num_requests} < {MIN_REQUESTS}")
    if failure_rate > MAX_FAILURE_RATE:
        failures.append(f"failure rate {failure_rate:.2f}% > {MAX_FAILURE_RATE:.2f}%")
    if total.num_requests and p95_ms > MAX_P95_MS:
        failures.append(f"p95 {p95_ms:.0f}ms > {MAX_P95_MS:.0f}ms")
    if rps < MIN_RPS:
        failures.append(f"RPS {rps:.2f} < {MIN_RPS:.2f}")

    if failures:
        environment.process_exit_code = 1
        print(f"LOAD TEST THRESHOLD FAILURE: {'; '.join(failures)}")


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
