import requests
import uuid
from datetime import datetime
import json

# API base URL
API_URL = "http://localhost:8000/api/v1"

def create_test_user():
    """Create a test user and return the user ID"""
    # For now, we'll just generate a UUID since we don't have a user creation endpoint
    return uuid.uuid4()

def submit_kyc_request(user_id):
    """Submit a KYC request with test data"""
    url = f"{API_URL}/kyc/submit"
    
    # Test data
    data = {
        "user_id": str(user_id),
        "full_name": "Test User",
        "dob": "1990-01-01",
        "address": "123 Test Street, Test City",
        "email": "test@example.com",
        "phone": "+84123456789",
        "doc_front_url": "https://example.com/test_doc_front.jpg",
        "doc_back_url": "https://example.com/test_doc_back.jpg",
        "selfie_url": "https://example.com/test_selfie.jpg"
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error submitting KYC request: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None

def check_kyc_status(ticket_id):
    """Check the status of a KYC request"""
    url = f"{API_URL}/kyc/status/{ticket_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error checking KYC status: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None

def main():
    # Create test user
    user_id = create_test_user()
    print(f"Created test user with ID: {user_id}")
    
    # Submit KYC request
    print("\nSubmitting KYC request...")
    result = submit_kyc_request(user_id)
    if not result:
        print("Failed to submit KYC request")
        return
    
    ticket_id = result["ticket_id"]
    print(f"KYC request submitted successfully. Ticket ID: {ticket_id}")
    
    # Check status
    print("\nChecking KYC status...")
    status = check_kyc_status(ticket_id)
    if status:
        print("KYC Status:")
        print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main() 