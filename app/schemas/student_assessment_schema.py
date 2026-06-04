from typing import Optional
from datetime import datetime
from app.schemas.base_schema import CamelModel

class StudentAssessmentCreate(CamelModel):
    assessment_id: int
    student_name: str
    student_class: str
    date_of_birth: str  # YYYY-MM-DD
    student_email: str
    contact: str  # Contact number

class StudentAssessmentResponse(CamelModel):
    id: int
    assessment_id: int
    student_name: str
    student_class: str
    date_of_birth: str
    student_email: str
    contact: str
    token: str
    created_at: datetime
    expires_at: datetime
    is_used: bool
    session_id: Optional[str] = None
    status: str
    assessment_link: str
    email_content: str

    class Config:
        from_attributes = True

class StudentAssessmentVerifyResponse(CamelModel):
    valid: bool
    reason: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    assessment_title: Optional[str] = None
    subject_name: Optional[str] = None
    class_name: Optional[str] = None

class StudentAssessmentStartRequest(CamelModel):
    token: str
    email: str
