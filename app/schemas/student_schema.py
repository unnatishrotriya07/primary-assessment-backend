from typing import Optional, List
from app.schemas.base_schema import CamelModel

class StudentBase(CamelModel):
    name: str
    email: str
    contact_number: Optional[str] = None
    scholar_number: str
    picture_url: Optional[str] = None
    class_id: int
    teacher_notes: Optional[str] = None

class StudentCreate(StudentBase):
    pass

class StudentUpdate(CamelModel):
    name: Optional[str] = None
    email: Optional[str] = None
    contact_number: Optional[str] = None
    scholar_number: Optional[str] = None
    picture_url: Optional[str] = None
    class_id: Optional[int] = None
    teacher_notes: Optional[str] = None

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

class ChapterMasteryResponse(CamelModel):
    id: int
    number: str
    title: str
    status: str
    score: Optional[float] = None
    assessments_count: int

class SubjectMasteryResponse(CamelModel):
    subject_id: int
    subject_name: str
    subject_code: str
    mastery_score: Optional[float] = None
    current_chapter: Optional[dict] = None
    suggested_next_chapter: Optional[dict] = None
    chapters: List[ChapterMasteryResponse]

class JourneyTimelineEventResponse(CamelModel):
    type: str
    date: str
    title: str
    description: str
    grade: Optional[str] = None
    score: Optional[float] = None
    subscores: Optional[dict] = None
    achievements: Optional[List[str]] = None

class JourneyAchievementResponse(CamelModel):
    id: str
    title: str
    description: str
    type: str
    date: str

class JourneyTrendDataResponse(CamelModel):
    date: str
    assessment_title: str
    overall_score: float
    communication: Optional[float] = None
    numeracy: Optional[float] = None
    creativity: Optional[float] = None
    emotional_iq: Optional[float] = None

class StudentJourneyResponse(CamelModel):
    student: StudentResponse
    parent_summary: str
    strengths: List[str]
    improvements: List[str]
    teacher_recommendations: List[str]
    teacher_notes: List[str]
    achievements: List[JourneyAchievementResponse]
    subjects: List[SubjectMasteryResponse]
    timeline: List[JourneyTimelineEventResponse]
    trend_data: List[JourneyTrendDataResponse]
