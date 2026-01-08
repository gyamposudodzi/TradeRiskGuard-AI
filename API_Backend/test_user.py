"""
Test script for User Management API
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def print_response(response, label=""):
    print(f"\n{'='*60}")
    if label:
        print(f"📋 {label}")
    print(f"Status Code: {response.status_code}")
    try:
        print("Response Body:")
        print(json.dumps(response.json(), indent=2))
    except:
        print(f"Raw Response: {response.text}")
    print('='*60)

def test_user_registration():
    """Test user registration"""
    print("🧪 Testing User Registration")
    
    payload = {
        "email": "trader2@example.com",
        "username": "trader2",
        "password": "SecurePass1234!"
    }
    
    #old payload = {"email": "trader1@example.com",
     #   "username": "trader1",
    #    "password": "SecurePass123!"
    #}
    
    response = requests.post(
        f"{BASE_URL}/api/users/register",
        json=payload
    )
    
    print_response(response, "Registration Response")
    return response.json() if response.status_code == 200 else None

def test_user_login():
    """Test user login"""
    print("\n🧪 Testing User Login")
    
    payload = {
        "email": "trader2@example.com",
        "password": "SecurePass1234!"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/users/login",
        json=payload
    )
    
    print_response(response, "Login Response")
    
    if response.status_code == 200:
        data = response.json()
        return data.get("data", {}).get("access_token")
    return None

def test_user_profile(token):
    """Test getting user profile with token"""
    print("\n🧪 Testing User Profile (Protected Route)")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/api/users/profile",
        headers=headers
    )
    
    print_response(response, "Profile Response")

def test_user_settings(token):
    """Test user settings endpoints"""
    print("\n🧪 Testing User Settings")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Get current settings
    response = requests.get(
        f"{BASE_URL}/api/users/settings",
        headers=headers
    )
    print_response(response, "Current Settings")
    
    # Update settings
    update_payload = {
        "max_position_size_pct": 3.0,
        "min_win_rate": 35.0,
        "ai_enabled": True
    }
    
    response = requests.put(
        f"{BASE_URL}/api/users/settings",
        headers=headers,
        json=update_payload
    )
    print_response(response, "Updated Settings")

def test_invalid_requests():
    """Test error cases"""
    print("\n🧪 Testing Invalid Requests")
    
    # Test duplicate registration
    payload = {
        "email": "trader1@example.com",
        "username": "trader1",
        "password": "AnotherPass123!"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/users/register",
        json=payload
    )
    print_response(response, "Duplicate Registration (Should Fail)")
    
    # Test invalid login
    payload = {
        "email": "trader1@example.com",
        "password": "WrongPassword"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/users/login",
        json=payload
    )
    print_response(response, "Invalid Login (Should Fail)")
    
    # Test profile without token
    response = requests.get(f"{BASE_URL}/api/users/profile")
    print_response(response, "Profile Without Token (Should Fail)")

def main():
    """Run all tests"""
    print("🧪 Starting User Management API Tests")
    print("="*60)
    
    # Test registration
    registration_result = test_user_registration()
    
    if registration_result and registration_result.get("success"):
        # Save token from registration
        reg_token = registration_result.get("data", {}).get("access_token")
        
        # Test login (should get new token)
        login_token = test_user_login()
        
        # Use the login token for further tests
        if login_token:
            test_user_profile(login_token)
            test_user_settings(login_token)
        
        # Also test with registration token
        if reg_token:
            print("\n🧪 Testing with Registration Token")
            test_user_profile(reg_token)
    
    # Test error cases
    test_invalid_requests()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()