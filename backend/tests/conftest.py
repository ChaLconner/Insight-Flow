import pytest
import os
import sys
from starlette.testclient import TestClient

# Add backend to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

@pytest.fixture(scope="module")
def client():
    # Set testing environment variables
    os.environ["TESTING"] = "true"
    with TestClient(app) as c:
        yield c
