import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.student_assessment import StudentAssessment
from app.models.assessment import Assessment

db = SessionLocal()
try:
    print("--- ASSESSMENTS ---")
    asmts = db.query(Assessment).all()
    for a in asmts:
        print(f"ID: {a.id} | Title: {a.title} | Subject ID: {a.subject_id} | Class ID: {a.class_id} | Status: {a.status}")

    print("\n--- STUDENT ASSIGNMENTS ---")
    sa_list = db.query(StudentAssessment).order_by(StudentAssessment.id.desc()).limit(10).all()
    for sa in sa_list:
        print(f"ID: {sa.id} | AsmtID: {sa.assessment_id} | Name: {sa.student_name} | Class: {sa.student_class} | DOB: {sa.date_of_birth} | Email: {sa.student_email} | Contact: {sa.contact} | Token: {sa.token[:8]}... | Status: {sa.status}")
finally:
    db.close()
