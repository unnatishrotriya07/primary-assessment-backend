import json
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.admin import Admin
from app.models.school import School

client = TestClient(app)

# 1. Clean up existing test admin/school if any
db = SessionLocal()
test_email = "director_test@example.com"
existing = db.query(Admin).filter(Admin.email == test_email).first()
if existing:
    tenant_id = existing.tenant_id
    db.delete(existing)
    if tenant_id:
        school = db.query(School).filter(School.tenant_id == tenant_id).first()
        if school:
            db.delete(school)
    db.commit()
db.close()

# 2. Register school & director
signup_payload = {
    "name": "Test Director",
    "email": test_email,
    "password": "password123",
    "schoolName": "Test School High"
}

print("Registering school...")
signup_res = client.post("/api/auth/signup", json=signup_payload)
print("Signup Status:", signup_res.status_code)
print("Signup Response JSON:")
print(json.dumps(signup_res.json(), indent=2))

# 3. Log in
login_payload = {
    "email": test_email,
    "password": "password123"
}

print("\nLogging in...")
login_res = client.post("/api/auth/login", json=login_payload)
print("Login Status:", login_res.status_code)
login_data = login_res.json()
print("Login Response JSON:")
print(json.dumps(login_data, indent=2))

token = login_data.get("token")
headers = {
    "Authorization": f"Bearer {token}"
}

# 4. Access Classes API
print("\nAccessing /classes/ endpoint...")
classes_res = client.get("/api/classes/", headers=headers)
print("Classes Status:", classes_res.status_code)
print("Classes Response JSON:")
try:
    print(json.dumps(classes_res.json()[:3], indent=2)) # Print first 3 classes
except Exception:
    print(classes_res.text)

# 5. Access Assessments API
print("\nAccessing /assessments/ endpoint...")
assessments_res = client.get("/api/assessments/", headers=headers)
print("Assessments Status:", assessments_res.status_code)
print("Assessments Response JSON:")
try:
    print(json.dumps(assessments_res.json(), indent=2))
except Exception:
    print(assessments_res.text)

# 6. Access Subjects API
print("\nAccessing /subjects/ endpoint...")
subjects_res = client.get("/api/subjects/", headers=headers)
print("Subjects Status:", subjects_res.status_code)
print("Subjects Response JSON:")
try:
    print(json.dumps(subjects_res.json()[:3], indent=2))
except Exception:
    print(subjects_res.text)
