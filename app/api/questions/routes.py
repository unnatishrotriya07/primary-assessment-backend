from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.schemas.question_schema import QuestionCreate, QuestionResponse, AIQuestionParams, QuestionBatchSave
from app.services.question_service import QuestionService

router = APIRouter()

@router.get("/", response_model=List[QuestionResponse])
def read_questions(
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    session: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = QuestionService(db)
    return service.get_questions(
        class_id=class_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        session=session,
        tenant_id=current_user.get("tenant_id")
    )

@router.post("/", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(question_in: QuestionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = QuestionService(db)
    return service.create_question(question_in, tenant_id=current_user.get("tenant_id"))

@router.post("/generate", response_model=List[QuestionResponse])
def generate_ai_questions(params: AIQuestionParams, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = QuestionService(db)
    return service.generate_ai_questions(params, tenant_id=current_user.get("tenant_id"))

@router.post("/batch", response_model=List[QuestionResponse])
def batch_create_questions(batch_in: QuestionBatchSave, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = QuestionService(db)
    return service.batch_create_questions(batch_in, tenant_id=current_user.get("tenant_id"))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = QuestionService(db)
    service.delete_question(id, tenant_id=current_user.get("tenant_id"))
    return None
