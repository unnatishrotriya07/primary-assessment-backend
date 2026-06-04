from typing import Optional, List, Dict
from app.schemas.question_schema import QuestionResponse
from app.schemas.base_schema import CamelModel

class AssessmentBase(CamelModel):
    title: str
    subject_id: int
    class_id: int
    status: Optional[str] = "Scheduled"
    date: Optional[str] = None
    questions_count: int

class AssessmentCreate(AssessmentBase):
    question_ids: Optional[List[int]] = None

class AssessmentResponse(AssessmentBase):
    id: int
    questions: Optional[List[QuestionResponse]] = []

class StartSessionResponse(CamelModel):
    session_id: str
    assessment: AssessmentResponse

class SubmitAnswersParams(CamelModel):
    session_id: str
    answers: Dict[str, str]

class SubmissionResultResponse(CamelModel):
    score: float
    result_id: str
