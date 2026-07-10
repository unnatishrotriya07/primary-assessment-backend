from pydantic import BaseModel
from typing import Optional, List
import datetime


class TranscriptEntry(BaseModel):
    role: str                            # "ai" or "student"
    text: str
    question_category: Optional[str] = None


class MessageCreateRequest(BaseModel):
    role: str
    text: str
    question_category: Optional[str] = None
    sequence_number: Optional[int] = None
    question_id: Optional[int] = None
    student_response: Optional[str] = None
    buddy_response: Optional[str] = None
    audio_url: Optional[str] = None
    speech_confidence: Optional[float] = None


class InterviewStartRequest(BaseModel):
    token: str
    email: str


class InterviewStartResponse(BaseModel):
    interview_id: int
    student_name: str
    student_class: str
    assessment_title: str
    questions: List[dict]
    subject_name: Optional[str] = None
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None

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
    questions: Optional[List[dict]] = None
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
    evaluated_answers: Optional[List[dict]] = None
    transcript: Optional[List[TranscriptEntry]] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    audio_references: Optional[List[str]] = None
    report_version: Optional[str] = None
    evaluation_steps: Optional[List[dict]] = None

    # Session variables
    current_question_index: int = 0
    session_state: str = "meet_buddy"
    comfort_index: int = 0
    raw_answers: Optional[List[dict]] = None
    network_status: str = "online"
    completion_status: str = "In Progress"

    # Human review
    requires_review: bool = False
    review_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime.datetime] = None
    raw_transcript: Optional[str] = None
    clean_transcript: Optional[str] = None
    validated_transcript: Optional[str] = None

    class Config:
        from_attributes = True


class SessionUpdateRequest(BaseModel):
    current_question_index: int
    session_state: str
    comfort_index: int
    raw_answers: Optional[List[dict]] = None
    network_status: str = "online"
    completion_status: str = "In Progress"


class InterviewReviewRequest(BaseModel):
    evaluated_answers: List[dict]
    admin_note: Optional[str] = None


class UpdateNotesRequest(BaseModel):
    admin_note: str