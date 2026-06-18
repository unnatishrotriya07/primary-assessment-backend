from typing import Optional, List
from app.schemas.base_schema import CamelModel

class StudentBase(CamelModel):
    name: str
    email: str
    contact_number: Optional[str] = None
    scholar_number: str
    picture_url: Optional[str] = None
    class_id: int

class StudentCreate(StudentBase):
    pass

class StudentUpdate(CamelModel):
    name: Optional[str] = None
    email: Optional[str] = None
    contact_number: Optional[str] = None
    scholar_number: Optional[str] = None
    picture_url: Optional[str] = None
    class_id: Optional[int] = None

class StudentResponse(StudentBase):
    id: int
    tenant_id: Optional[str] = None

class StudentReportResponse(CamelModel):
    id: int
    assessment_id: int
    assessment_title: str
    score: float
    grade: str
    duration: str
    accuracy: float
    completed_at: Optional[str] = None
    feedback: Optional[str] = None
