import io
import json
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.admin import Admin
from app.models.class_model import Class
from app.core.security import create_access_token

client = TestClient(app)

# 1. Authenticate as Admin
db = SessionLocal()
admin = db.query(Admin).filter(Admin.email == "admin@example.com").first()
if not admin:
    print("Admin user not found. Seeding first...")
    # Add dummy admin if not found
    from app.core.security import get_password_hash
    admin = Admin(email="admin@example.com", hashed_password=get_password_hash("password123"), role="admin", name="Admin")
    db.add(admin)
    db.commit()
    db.refresh(admin)

token = create_access_token(admin.email)

# Find a base class to use
base_class = db.query(Class).filter(Class.name == "Grade 1").first()
if not base_class:
    # Use any class
    base_class = db.query(Class).first()

if not base_class:
    print("No class found in DB. Creating one first...")
    base_class = Class(name="Grade 1", grade="1", section="A")
    db.add(base_class)
    db.commit()
    db.refresh(base_class)

base_class_id = base_class.id
print(f"Using Base Class ID: {base_class_id} (Grade {base_class.grade} Section {base_class.section})")
db.close()

headers = {
    "Authorization": f"Bearer {token}"
}

# 2. Build mock CSV content
csv_b = "Scholar Number,Student Name,Email Address,Contact Number\nB101,Student B One,b1@example.com,9998887771\nB102,Student B Two,b2@example.com,9998887772"
csv_c = "Scholar Number,Student Name,Email Address,Contact Number\nC101,Student C One,c1@example.com,9998887773\nC102,Student C Two,c2@example.com,9998887774"

files = [
    ("files", ("Roster_B.csv", io.BytesIO(csv_b.encode("utf-8")), "text/csv")),
    ("files", ("Roster_C.csv", io.BytesIO(csv_c.encode("utf-8")), "text/csv"))
]

sections_map = {
    "Roster_B.csv": "B",
    "Roster_C.csv": "C"
}

data = {
    "base_class_id": base_class_id,
    "sections_map": json.dumps(sections_map)
}

print("Sending bulk section upload request...")
response = client.post("/api/students/upload-multiple-sections", data=data, files=files, headers=headers)

print("Status Code:", response.status_code)
try:
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception:
    print("Response Text:", response.text)

# Verify DB changes
db = SessionLocal()
class_b = db.query(Class).filter(Class.name == base_class.name, Class.grade == base_class.grade, Class.section == "B").first()
class_c = db.query(Class).filter(Class.name == base_class.name, Class.grade == base_class.grade, Class.section == "C").first()

print("\n--- DB Verification ---")
if class_b:
    print(f"Class for Section B found! ID: {class_b.id}")
    print(f"  Subjects count: {len(class_b.subjects)}")
    for s in class_b.subjects:
        print(f"    Subject: {s.name} (Code: {s.code})")
        print(f"      Chapters count: {len(s.chapters)}")
else:
    print("Class for Section B NOT found!")

if class_c:
    print(f"Class for Section C found! ID: {class_c.id}")
    print(f"  Subjects count: {len(class_c.subjects)}")
else:
    print("Class for Section C NOT found!")

db.close()
