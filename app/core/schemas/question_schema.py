from datetime import datetime
from typing import List, Optional
from app.schemas.base_schema import CamelModel

class QuestionBase(CamelModel):
    text: str
    options: List[str]
    correct_answer: Optional[str] = None
    question_type: Optional[str] = "mcq"
    difficulty: str
    cognitive_level: str
    class_id: Optional[int] = None
    subject_id: int
    chapter_id: Optional[int] = None
    generated_by: Optional[str] = None
    session: Optional[str] = None
    created_at: Optional[datetime] = None
    source: Optional[str] = None
    section: Optional[str] = None
    page: Optional[str] = None
    confidence: Optional[int] = None
    reference_text: Optional[str] = None

class QuestionCreate(QuestionBase):
    pass

class QuestionResponse(QuestionBase):
    id: int

class AIQuestionParams(CamelModel):
    class_id: Optional[int] = None
    subject_id: int
    chapter_id: int
    difficulty: str
    cognitive_level: str
    count: int
    regenerate: Optional[bool] = False
    preview_only: Optional[bool] = False
    session: Optional[str] = None
    question_type: Optional[str] = "mixed"
    section_ids: Optional[List[int]] = None
    selected_text: Optional[str] = None

class QuestionBatchSave(CamelModel):
    questions: List[QuestionCreate]
    clear_existing: Optional[bool] = False
    chapter_id: Optional[int] = None
    difficulty: Optional[str] = None
    cognitive_level: Optional[str] = None

