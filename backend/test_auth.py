"""
Test script for authentication endpoints.
"""
import httpx
import json

BASE_URL = "http://localhost:8000"

def test_register():
    """Test user registration."""
    print("Testing user registration...")
    
    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword123"
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(f"{BASE_URL}/auth/register", json=user_data)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("Registration successful")
                return True
            else:
                print("Registration failed")
                return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_login():
    """Test user login."""
    print("\nTesting user login...")
    
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(f"{BASE_URL}/auth/login", json=login_data)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("Login successful")
                token_data = response.json()
                return token_data.get("access_token")
            else:
                print("Login failed")
                return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_protected_endpoint(token):
    """Test protected endpoint with token."""
    print("\nTesting protected endpoint...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{BASE_URL}/auth/me", headers=headers)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("Protected endpoint access successful")
                return True
            else:
                print("Protected endpoint access failed")
                return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Starting authentication tests...")
    
    # Test registration
    if test_register():
        # Test login
        token = test_login()
        if token:
            # Test protected endpoint
            test_protected_endpoint(token)
    
    print("\nAuthentication tests completed!")