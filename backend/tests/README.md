# API Test Suite for Insight-Flow

This comprehensive test suite covers all API endpoints for the Insight-Flow backend application.

## 📁 Test Structure

```
backend/tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest configuration and fixtures
├── pytest.ini               # Pytest configuration file
├── run_tests.py              # Test runner script
├── utils.py                  # Test utilities and helpers
├── README.md                 # This file
├── test_auth.py              # Authentication endpoint tests
├── test_users.py             # User management endpoint tests
├── test_projects.py          # Project management endpoint tests
├── test_tasks.py             # Task management endpoint tests
├── test_analytics.py         # Analytics endpoint tests
├── test_notifications.py     # Notification endpoint tests
└── test_integration.py        # Integration tests
```

## 🚀 Quick Start

### Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov pytest-asyncio pytest-mock
   ```

2. **Environment Setup**
   ```bash
   # Copy environment file
   cp .env.example .env
   
   # Set test database URL
   export TEST_DATABASE_URL="sqlite:///./test.db"
   ```

3. **Start API Server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Running Tests

#### Option 1: Interactive Test Runner
```bash
cd backend
python tests/run_tests.py
```

#### Option 2: Command Line
```bash
# Run all tests
pytest tests/

# Run specific module
pytest tests/test_auth.py

# Run with coverage
pytest --cov=. tests/

# Run integration tests only
pytest -m integration tests/

# Run unit tests only
pytest -m "not integration" tests/
```

#### Option 3: Test Runner Script
```bash
# Run all tests with coverage
python tests/run_tests.py --type all --coverage

# Run specific module tests
python tests/run_tests.py --module auth

# Run integration tests only
python tests/run_tests.py --type integration

# Run with verbose output
python tests/run_tests.py --verbose

# Run with parallel execution
python tests/run_tests.py --parallel 4
```

## 📊 Test Coverage

### Authentication Tests (`test_auth.py`)
- ✅ User registration
- ✅ User login
- ✅ Token validation
- ✅ Token refresh
- ✅ Google OAuth integration
- ✅ Error handling and validation

### User Management Tests (`test_users.py`)
- ✅ User CRUD operations
- ✅ User search functionality
- ✅ Profile updates
- ✅ Permission validation
- ✅ Input validation

### Project Management Tests (`test_projects.py`)
- ✅ Project CRUD operations
- ✅ Member management
- ✅ Role-based permissions
- ✅ Project access control
- ✅ Input validation

### Task Management Tests (`test_tasks.py`)
- ✅ Task CRUD operations
- ✅ Task assignment
- ✅ Status updates
- ✅ Project task filtering
- ✅ User task management

### Analytics Tests (`test_analytics.py`)
- ✅ Dashboard metrics
- ✅ Productivity data
- ✅ Team contributions
- ✅ Performance validation
- ✅ Data aggregation

### Notification Tests (`test_notifications.py`)
- ✅ Notification retrieval
- ✅ Read/unread status
- ✅ Bulk operations
- ✅ Filtering and pagination
- ✅ Integration workflows

### Integration Tests (`test_integration.py`)
- ✅ End-to-end workflows
- ✅ Multi-step operations
- ✅ Permission inheritance
- ✅ Cascade operations
- ✅ Performance validation

## 🛠️ Test Utilities

### TestDataManager
Manages creation and cleanup of test data:
```python
from tests.utils import TestDataManager

# In test fixture or test method
data_manager = TestDataManager(db_session)
user = data_manager.create_test_user()
project = data_manager.create_test_project(user.id)
data_manager.cleanup()  # Clean up all created data
```

### AuthHelper
Authentication utilities for testing:
```python
from tests.utils import AuthHelper

# Create test token
token = AuthHelper.create_test_token("user_id")
headers = AuthHelper.create_headers(token)

# Create expired token
expired_token = AuthHelper.create_expired_token("user_id")
```

### ResponseValidator
Response validation helpers:
```python
from tests.utils import ResponseValidator

# Validate success response
ResponseValidator.assert_success_response(response, 200)

# Validate error response
ResponseValidator.assert_error_response(response, 404, "Not found")

# Validate pagination structure
ResponseValidator.assert_pagination_structure(response.json())
```

## 🏷️ Test Markers

Use pytest markers to categorize tests:

```bash
# Run specific test categories
pytest -m auth              # Authentication tests
pytest -m user              # User management tests
pytest -m project           # Project management tests
pytest -m task              # Task management tests
pytest -m analytics          # Analytics tests
pytest -m notification       # Notification tests
pytest -m integration        # Integration tests
pytest -m unit              # Unit tests only
pytest -m slow              # Slow tests
```

## 📋 Test Scenarios

### Basic Workflow Tests
1. **User Registration → Login → Profile Update**
2. **Project Creation → Member Addition → Task Creation**
3. **Task Assignment → Status Updates → Completion**
4. **Analytics Data Generation → Dashboard Retrieval**

### Error Handling Tests
1. **Invalid Input Validation**
2. **Permission Denied Scenarios**
3. **Resource Not Found Cases**
4. **Authentication Failures**

### Performance Tests
1. **Concurrent Request Handling**
2. **Response Time Validation**
3. **Database Query Performance**
4. **Memory Usage Validation**

## 🔧 Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Coverage settings
- Warning filters
- Marker definitions

### Environment Variables
```bash
# Test database
TEST_DATABASE_URL="sqlite:///./test.db"

# API base URL
API_BASE_URL="http://localhost:8000"

# Test mode
TESTING=true

# Coverage threshold
COVERAGE_THRESHOLD=80
```

## 📈 Coverage Reports

Generate comprehensive coverage reports:

```bash
# HTML coverage report
pytest --cov=. --cov-report=html tests/

# Terminal coverage report
pytest --cov=. --cov-report=term-missing tests/

# Coverage with minimum threshold
pytest --cov=. --cov-fail-under=80 tests/
```

Coverage reports are generated in:
- `htmlcov/index.html` - Interactive HTML report
- Terminal output with missing lines

## 🐛 Debugging Tests

### Running Individual Tests
```bash
# Run specific test method
pytest tests/test_auth.py::TestAuthentication::test_login_success -v

# Run with debugging
pytest tests/test_auth.py::test_login_success -s --tb=long

# Run with pdb
pytest tests/test_auth.py::test_login_success --pdb
```

### Test Database Inspection
```bash
# Open test database
sqlite3 test.db

# View tables
.tables

# View data
SELECT * FROM users;
SELECT * FROM projects;
SELECT * FROM tasks;
```

## 🚨 Common Issues

### Database Connection Issues
```bash
# Check database file exists
ls -la test.db

# Check database permissions
sqlite3 test.db ".tables"

# Recreate test database
rm test.db
python -c "from database import engine, Base; Base.metadata.create_all(engine)"
```

### Import Errors
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Install missing dependencies
pip install -r requirements.txt

# Check module imports
python -c "from tests.conftest import *; print('Imports OK')"
```

### Authentication Issues
```bash
# Check JWT secret
python -c "from utils.auth import *; print('Auth OK')"

# Test token generation
python -c "from tests.utils import AuthHelper; print(AuthHelper.create_test_token('test'))"
```

## 📝 Writing New Tests

### Test Structure Template
```python
import pytest
from fastapi.testclient import TestClient

class TestNewFeature:
    """Test new feature endpoints."""
    
    def test_success_case(self, client: TestClient, auth_headers: dict):
        """Test successful operation."""
        # Arrange
        test_data = {"key": "value"}
        
        # Act
        response = client.post("/endpoint", json=test_data, headers=auth_headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "expected_value"
    
    def test_error_case(self, client: TestClient):
        """Test error handling."""
        # Arrange
        invalid_data = {"key": "invalid"}
        
        # Act
        response = client.post("/endpoint", json=invalid_data)
        
        # Assert
        assert response.status_code == 422
```

### Best Practices
1. **Use descriptive test names**
2. **Follow Arrange-Act-Assert pattern**
3. **Test both success and failure cases**
4. **Use fixtures for common setup**
5. **Validate response structure**
6. **Test authentication and authorization**
7. **Include performance assertions**
8. **Add proper error messages**

## 🔄 Continuous Integration

### GitHub Actions Example
```yaml
name: API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    - name: Run tests
      run: |
        pytest tests/ --cov=. --cov-fail-under=80
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

## 📞 Support

For test-related issues:
1. Check the test logs for detailed error messages
2. Verify API server is running on correct port
3. Ensure test database is properly configured
4. Check all dependencies are installed
5. Review pytest configuration

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Test Coverage](https://coverage.readthedocs.io/)
- [HTTPX Testing](https://www.python-httpx.org/)