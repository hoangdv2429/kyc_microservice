import requests
import json
import uuid
from pathlib import Path
import time

# Configuration
API_URL = "http://localhost:8001"
TEST_DATA_DIR = Path("test_data")

def upload_file(file_path: Path) -> str:
    """Upload a file to MinIO and return the URL."""
    # In a real scenario, this would use presigned URLs
    # For testing, we'll just return a mock URL
    return f"http://minio:9000/kyc-documents/{file_path.name}"

def test_kyc_flow():
    # 1. Prepare test data
    test_user_id = str(uuid.uuid4())
    
    # Upload test files
    doc_front_url = upload_file(TEST_DATA_DIR / "id_front.jpg")
    doc_back_url = upload_file(TEST_DATA_DIR / "id_back.jpg")
    selfie_url = upload_file(TEST_DATA_DIR / "selfie.jpg")
    
    # 2. Submit KYC request
    kyc_data = {
        "user_id": test_user_id,
        "doc_front_url": doc_front_url,
        "doc_back_url": doc_back_url,
        "selfie_url": selfie_url
    }
    
    print("Submitting KYC request...")
    response = requests.post(f"{API_URL}/api/v1/kyc/submit", json=kyc_data)
    response.raise_for_status()
    ticket_id = response.json()["ticket_id"]
    print(f"KYC request submitted. Ticket ID: {ticket_id}")
    
    # 3. Poll for status
    print("\nPolling for KYC status...")
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(f"{API_URL}/api/v1/kyc/status/{ticket_id}")
        response.raise_for_status()
        status = response.json()
        
        print(f"\nAttempt {attempt + 1}/{max_attempts}")
        print(f"Status: {status['status']}")
        if status.get("ocr_json"):
            print("OCR Results:")
            print(json.dumps(status["ocr_json"], indent=2))
        if status.get("face_score") is not None:
            print(f"Face Match Score: {status['face_score']}")
        if status.get("sanctions_hit"):
            print("Sanctions Check Results:")
            print(json.dumps(status["sanctions_hit"], indent=2))
            
        if status["status"] != "pending":
            break
            
        time.sleep(5)  # Wait 5 seconds between polls
        attempt += 1
    
    # 4. Check admin endpoints
    print("\nChecking admin endpoints...")
    response = requests.get(f"{API_URL}/api/v1/admin/pending")
    response.raise_for_status()
    pending_jobs = response.json()
    print(f"Pending jobs: {len(pending_jobs)}")
    
    # 5. Review the KYC job
    if pending_jobs:
        review_data = {
            "reviewer_id": str(uuid.uuid4()),
            "decision": "passed",
            "note": "Test review"
        }
        response = requests.post(
            f"{API_URL}/api/v1/admin/review/{ticket_id}",
            json=review_data
        )
        response.raise_for_status()
        print("Review submitted successfully")

if __name__ == "__main__":
    test_kyc_flow() 