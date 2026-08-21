from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class AiStartRequest(BaseModel):
    token: str = Field(..., description="Student assessment token.")
    email: str = Field(..., description="Student email from Google sign-in.")


class AiStartResponse(BaseModel):
    interview_id: int
    student_name: str
    student_class: str
    assessment_title: Optional[str] = None
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    subject_name: Optional[str] = None


class AiTurnRequest(BaseModel):
    student_response: str = Field("", description="Transcribed student speech.")
    audio_url: Optional[str] = None


class AiTurnResponse(BaseModel):
    interview_id: int
    next_speech: str
    next_state: str
    action: str
    current_question_index: int
    comfort_index: int
    hints_remaining: int
    active_hint: Optional[str] = None
    completion_status: str


class AiSTTResponse(BaseModel):
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    duration: Optional[float] = None
    error: Optional[str] = None


class AiTTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    speed: float = Field(1.0, ge=0.5, le=2.0)


class AiSessionResponse(BaseModel):
    interview_id: int
    student_name: str
    student_class: str
    session_state: str
    current_question_index: int
    comfort_index: int
    completion_status: str
    status: str
    transcript: List[Dict[str, str]] = Field(default_factory=list)


class AiHealthResponse(BaseModel):
    status: str
    stt: str
    tts: str
