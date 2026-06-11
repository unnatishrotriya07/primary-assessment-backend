from typing import List
import uuid
from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.schemas.assessment_schema import (
    AssessmentCreate, AssessmentResponse, StartSessionResponse,
    SubmitAnswersParams, SubmissionResultResponse
)
from app.services.assessment_service import AssessmentService
from app.schemas.student_assessment_schema import (
    StudentAssessmentCreate, StudentAssessmentResponse,
    StudentAssessmentVerifyResponse, StudentAssessmentStartRequest
)
from app.services.student_assessment_service import StudentAssessmentService

router = APIRouter()

@router.get("/", response_model=List[AssessmentResponse])
def read_assessments(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = AssessmentService(db)
    return service.get_all_assessments(tenant_id=current_user.get("tenant_id"))

@router.post("/", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(asmt_in: AssessmentCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = AssessmentService(db)
    return service.create_assessment(asmt_in, tenant_id=current_user.get("tenant_id"))

@router.get("/verify-token", response_model=StudentAssessmentVerifyResponse)
def verify_token(token: str, email: str, db: Session = Depends(get_db)):
    service = StudentAssessmentService(db)
    return service.verify_token(token, email)


@router.get("/{id}", response_model=AssessmentResponse)
def read_assessment(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = AssessmentService(db)
    asmt = service.get_assessment_by_id(id, tenant_id=current_user.get("tenant_id"))
    return asmt

@router.post("/{id}/start", response_model=StartSessionResponse)
def start_assessment_session(id: int, db: Session = Depends(get_db)):
    # Students starting testing session don't need auth check in demo
    service = AssessmentService(db)
    asmt = service.get_assessment_by_id(id)
    questions = service.get_questions_for_session(id)
    
    # Format questions response and omit correct answers for student safety
    sanitized_questions = []
    for q in questions:
        sanitized_questions.append({
            "id": q.id,
            "text": q.text,
            "options": q.options,
            "difficulty": q.difficulty,
            "cognitive_level": q.cognitive_level,
            "subject_id": q.subject_id,
            "chapter_id": q.chapter_id
        })
        
    session_id = f"asmt_{id}_{uuid.uuid4().hex[:8]}"
    
    return StartSessionResponse(
        session_id=session_id,
        assessment=AssessmentResponse(
            id=asmt.id,
            title=asmt.title,
            subject_id=asmt.subject_id,
            class_id=asmt.class_id,
            status=asmt.status,
            date=asmt.date,
            questions_count=asmt.questions_count,
            questions=sanitized_questions
        )
    )

@router.post("/submit", response_model=SubmissionResultResponse)
def submit_answers(params: SubmitAnswersParams, db: Session = Depends(get_db)):
    service = AssessmentService(db)
    return service.submit_session_answers(params, db)

# Student Invitation & Verification endpoints

@router.post("/assign", response_model=StudentAssessmentResponse)
def assign_assessment(
    payload: StudentAssessmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Extract calling host scheme and domain dynamically from Origin/Referer headers
    origin = request.headers.get("origin") or request.headers.get("referer")
    frontend_url = None
    if origin and "://" in origin:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        frontend_url = f"{parsed.scheme}://{parsed.netloc}"
        
    service = StudentAssessmentService(db)
    return service.assign_assessment(payload, tenant_id=current_user.get("tenant_id"), frontend_url=frontend_url)

@router.post("/start-by-token")
def start_assessment_by_token(payload: StudentAssessmentStartRequest, db: Session = Depends(get_db)):
    service = StudentAssessmentService(db)
    try:
        return service.start_session_by_token(payload.token, payload.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
