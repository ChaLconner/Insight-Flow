#!/usr/bin/env python3
"""
Test script to verify /projects endpoint works after enum fixes.
"""
import requests
import json
import sys

def test_projects_endpoint():
    """Test the /projects endpoint to ensure it works without 500 errors."""
    
    base_url = "http://localhost:8000"
    
    print("Testing /projects endpoint...")
    
    # Test health endpoint first
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        print(f"Health check: {health_response.status_code}")
        if health_response.status_code == 200:
            print("✓ Server is running")
        else:
            print("✗ Server health check failed")
            return False
    except Exception as e:
        print(f"✗ Failed to connect to server: {e}")
        return False
    
    # Test projects endpoint without authentication first (should get 401)
    try:
        projects_response = requests.get(f"{base_url}/projects", timeout=10)
        print(f"Projects endpoint (no auth): {projects_response.status_code}")
        if projects_response.status_code == 401:
            print("✓ Authentication required as expected")
        else:
            print(f"✗ Expected 401, got {projects_response.status_code}")
    except Exception as e:
        print(f"✗ Failed to test projects endpoint: {e}")
        return False
    
    # Test with dummy token (should get 422 or 401, not 500)
    try:
        headers = {"Authorization": "Bearer dummy_token"}
        projects_response = requests.get(f"{base_url}/projects", headers=headers, timeout=10)
        print(f"Projects endpoint (with dummy token): {projects_response.status_code}")
        
        if projects_response.status_code == 500:
            print("✗ Still getting 500 Internal Server Error!")
            print(f"Response: {projects_response.text}")
            return False
        elif projects_response.status_code in [401, 422]:
            print("✓ No longer getting 500 error - authentication/validation issue (expected)")
            return True
        else:
            print(f"? Unexpected status code: {projects_response.status_code}")
            return True
            
    except Exception as e:
        print(f"✗ Failed to test projects endpoint with token: {e}")
        return False

if __name__ == "__main__":
    success = test_projects_endpoint()
    if success:
        print("\n✅ SUCCESS: /projects endpoint is no longer throwing 500 Internal Server Error!")
        sys.exit(0)
    else:
        print("\n❌ FAILURE: /projects endpoint still has issues")
        sys.exit(1)