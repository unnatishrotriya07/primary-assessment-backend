from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.admin import Admin
from app.core.security import create_access_token
import json

client = TestClient(app)

db = SessionLocal()
admin = db.query(Admin).filter(Admin.email == "admin@example.com").first()
if not admin:
    print("Admin user not found.")
    db.close()
    exit(1)

token = create_access_token(admin.email)
db.close()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

payload = {
    "title": "Custom Test Assessment",
    "subjectId": 3,
    "classId": 3,
    "status": "Active",
    "date": "2026-05-30",
    "questionsCount": 2,
    "questionIds": [2, 3]
}

print("Sending create assessment request...")
response = client.post("/api/assessments/", json=payload, headers=headers)
print("Status Code:", response.status_code)
print("Response:")
try:
    print(json.dumps(response.json(), indent=2))
except Exception:
    print(response.text)
