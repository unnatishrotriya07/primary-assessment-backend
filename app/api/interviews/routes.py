from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.schemas.interview_schema import (
    InterviewStartRequest,
    InterviewStartResponse,
    InterviewSubmitRequest,
    InterviewReportResponse,
)
from app.services.interview_service import InterviewService

router = APIRouter()


# ── No auth needed — student-facing ──────────────────────────────────────────

@router.post("/start", response_model=InterviewStartResponse)
def start_interview(payload: InterviewStartRequest, db: Session = Depends(get_db)):
    """
    Called right after Google sign-in on the verify page.
    Creates the Interview row in the database and returns
    the student's name and the 7 interview questions.
    """
    service = InterviewService(db)
    try:
        result = service.start_interview(payload.token, payload.email)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submit", response_model=InterviewReportResponse, status_code=202)
def submit_interview(
    payload: InterviewSubmitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Called when the student finishes all 7 questions.
    Saves the transcript and starts evaluation in the background.
    Returns the report immediately in 'Evaluating' status.
    """
    service = InterviewService(db)
    try:
        interview = service.save_submission_and_set_evaluating(payload)
        qa_eval_context = service.prepare_eval_context(interview, payload.answers)
        background_tasks.add_task(
            service.evaluate_interview_in_background,
            interview.id,
            qa_eval_context
        )
        return _build_response(interview)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{interview_id}", response_model=InterviewReportResponse)
def get_interview_report(
    interview_id: int,
    db: Session = Depends(get_db),
):
    """
    Student/Admin: fetch one completed interview report by ID.
    Allows student fallback report loading without auth.
    """
    service = InterviewService(db)
    try:
        return _build_response(service.get_report(interview_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Auth required — admin-facing ──────────────────────────────────────────────

@router.get("/assessment/{assessment_id}", response_model=List[InterviewReportResponse])
def get_interviews_for_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Admin: get all completed interviews for one assessment.
    Used in the admin reports/dashboard page.
    """
    from app.models.assessment import Assessment
    asmt_query = db.query(Assessment).filter(Assessment.id == assessment_id)
    if current_user.get("tenant_id") is not None:
        asmt_query = asmt_query.filter(Assessment.tenant_id == current_user.get("tenant_id"))
    asmt = asmt_query.first()
    if not asmt:
        raise HTTPException(status_code=404, detail="Assessment not found")

    service = InterviewService(db)
    return [_build_response(iv) for iv in service.get_reports_for_assessment(assessment_id)]





# ── Helper to map SQLAlchemy model → Pydantic response ───────────────────────

def _build_response(iv) -> InterviewReportResponse:
    return InterviewReportResponse(
        id=iv.id,
        student_name=iv.student_name,
        student_class=iv.student_class,
        assessment_title=iv.assessment.title if iv.assessment else None,
        overall_score=iv.overall_score,
        grade=iv.grade,
        recommendation=iv.recommendation,
        score_communication=iv.score_communication,
        score_numeracy=iv.score_numeracy,
        score_creativity=iv.score_creativity,
        score_emotional_iq=iv.score_emotional_iq,
        strengths=iv.strengths,
        improvements=iv.improvements,
        admin_note=iv.admin_note,
        summary=iv.summary,
        status=iv.status,
        started_at=iv.started_at,
        completed_at=iv.completed_at,
        evaluated_answers=iv.evaluated_answers,
    )