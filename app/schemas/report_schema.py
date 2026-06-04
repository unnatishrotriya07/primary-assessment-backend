from typing import Optional, List
from app.schemas.base_schema import CamelModel

class ReportBase(CamelModel):
    assessment_id: int
    student_name: str
    score: float
    grade: str
    duration: str
    accuracy: float
    completed_at: Optional[str] = None
    feedback: Optional[str] = None

class ReportResponse(ReportBase):
    id: int

class ReportOverviewResponse(CamelModel):
    total_students: int
    passing_rate: float
