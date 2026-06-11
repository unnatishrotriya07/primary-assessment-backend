import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../../Documents/Codebase/primary_ assessment/backend')))

from app.db.session import SessionLocal
from app.services.student_assessment_service import StudentAssessmentService
from app.schemas.student_assessment_schema import StudentAssessmentCreate
from app.models.assessment import Assessment

db = SessionLocal()
try:
    asmt = db.query(Assessment).first()
    if not asmt:
        print("No assessments found in DB!")
        sys.exit(1)
        
    print(f"Using Assessment ID: {asmt.id}")
    
    payload = StudentAssessmentCreate(
        assessment_id=asmt.id,
        student_name="Test Student",
        student_class="Class 4",
        date_of_birth="2015-05-05",
        student_email="test@example.com",
        contact="1234567890"
    )
    
    service = StudentAssessmentService(db)
    res = service.assign_assessment(payload, frontend_url="https://my-custom-production-domain.com")
    
    print("Generated assessment link:")
    print(res.assessment_link)
    print("\nGenerated email content:")
    print(res.email_content)
    
    if "https://my-custom-production-domain.com" in res.assessment_link and "https://my-custom-production-domain.com" in res.email_content:
        print("\nSUCCESS: Link and email content were correctly generated with the custom production Origin domain!")
    else:
        print("\nFAILURE: Custom Origin was not used in link generation.")
finally:
    db.close()
