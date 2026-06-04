from pydantic import BaseModel
from typing import Optional, List
import datetime


class TranscriptEntry(BaseModel):
    role: str                            # "ai" or "student"
    text: str
    question_category: Optional[str] = None


class InterviewStartRequest(BaseModel):
    token: str
    email: str


class InterviewStartResponse(BaseModel):
    interview_id: int
    student_name: str
    student_class: str
    assessment_title: str
    questions: List[dict]

    class Config:
        from_attributes = True


class InterviewSubmitRequest(BaseModel):
    interview_id: int
    transcript: List[TranscriptEntry]
    # Each entry: {"question_category": "...", "question": "...", "answer": "..."}
    answers: List[dict]


class InterviewReportResponse(BaseModel):
    id: int
    student_name: str
    student_class: str
    assessment_title: Optional[str] = None
    overall_score: Optional[float] = None
    grade: Optional[str] = None
    recommendation: Optional[str] = None
    score_communication: Optional[float] = None
    score_numeracy: Optional[float] = None
    score_creativity: Optional[float] = None
    score_emotional_iq: Optional[float] = None
    strengths: Optional[str] = None
    improvements: Optional[str] = None
    admin_note: Optional[str] = None
    summary: Optional[str] = None
    status: str
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True