from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.admin import Admin
from app.core.security import create_access_token
import json

client = TestClient(app)

# Create access token for admin
db = SessionLocal()
admin = db.query(Admin).filter(Admin.email == "admin@example.com").first()
if not admin:
    print("Admin user not found, cannot run test.")
    db.close()
    exit(1)

token = create_access_token(admin.email)
db.close()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Payload to assign Assessment ID 2 (which exists in DB)
payload = {
    "assessmentId": 2,
    "studentName": "Integration Test Student",
    "studentClass": "Grade 1-B",
    "dateOfBirth": "2018-05-15",
    "studentEmail": "teststudent@example.com",
    "contact": "9876543210"
}

print("Sending assign request...")
response = client.post("/api/assessments/assign", json=payload, headers=headers)
print("Status Code:", response.status_code)
print("Response JSON:")
try:
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(response.text)
