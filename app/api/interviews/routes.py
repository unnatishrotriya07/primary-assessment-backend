from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.schemas.interview_schema import (
    InterviewStartRequest,
    InterviewStartResponse,
    InterviewSubmitRequest,
    InterviewReportResponse,
    UpdateNotesRequest,
    SessionUpdateRequest,
    InterviewReviewRequest,
    MessageCreateRequest,
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



@router.post("/{interview_id}/messages")
def record_interview_message(
    interview_id: int,
    payload: MessageCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Called in real-time by student interface to persist turn history turn-by-turn.
    """
    service = InterviewService(db)
    try:
        msg = service.add_message(
            interview_id=interview_id,
            role=payload.role,
            text=payload.text,
            question_category=payload.question_category,
            sequence_number=payload.sequence_number,
            question_id=payload.question_id,
            student_response=payload.student_response,
            buddy_response=payload.buddy_response,
            audio_url=payload.audio_url,
            speech_confidence=payload.speech_confidence,
        )
        return {"status": "success", "message_id": msg.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/submit", response_model=InterviewReportResponse, status_code=202)
def submit_interview(
    payload: InterviewSubmitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Called when the student finishes all 7 questions.
    Saves the transcript and starts evaluation in the background.
    """
    service = InterviewService(db)
    try:
        interview = service.save_submission_and_set_evaluating(payload)
        
        # Check if Redis is alive before calling Celery
        redis_alive = False
        try:
            import redis
            from app.core.config import settings
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=0.5, socket_connect_timeout=0.5)
            r.ping()
            redis_alive = True
        except Exception:
            redis_alive = False

        if redis_alive:
            # Async Celery pipeline trigger
            try:
                from app.tasks.evaluation_tasks import evaluate_interview_task
                evaluate_interview_task.delay(interview.id)
                print(f"[Routes] Enqueued evaluation task via Celery for interview {interview.id}", flush=True)
            except Exception as celery_err:
                print(f"[Routes] Celery connection failed: {celery_err}. Falling back to BackgroundTasks.", flush=True)
                background_tasks.add_task(
                    service.evaluate_interview_in_background_v2,
                    interview.id
                )
        else:
            print("[Routes] Redis not reachable. Falling back to BackgroundTasks directly.", flush=True)
            background_tasks.add_task(
                service.evaluate_interview_in_background_v2,
                interview.id
            )
            
        return _build_response(interview)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{interview_id}/regenerate")
def regenerate_interview_report(
    interview_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Teacher/Admin: trigger V2 prompt/worker regeneration of evaluations from transcript messages.
    """
    service = InterviewService(db)
    try:
        # Fetch report details
        interview = service.get_report(interview_id)
        # Update status back to Transcript Saved
        interview.status = "Transcript Saved"
        db.commit()
        
        try:
            from app.tasks.evaluation_tasks import evaluate_interview_task
            evaluate_interview_task.delay(interview.id)
            print(f"[Routes] Enqueued regeneration task via Celery for interview {interview.id}", flush=True)
        except Exception as celery_err:
            print(f"[Routes] Celery connection failed: {celery_err}. Falling back to BackgroundTasks.", flush=True)
            background_tasks.add_task(
                service.evaluate_interview_in_background_v2,
                interview.id
            )
        return {"status": "success", "message": "Evaluation regeneration started"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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





@router.put("/{interview_id}/notes", response_model=InterviewReportResponse)
def update_interview_notes(
    interview_id: int,
    payload: UpdateNotesRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Teacher/Admin: Update observation notes for a student's interview.
    """
    service = InterviewService(db)
    try:
        updated = service.update_notes(interview_id, payload.admin_note)
        return _build_response(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{interview_id}/session", response_model=InterviewReportResponse)
def update_interview_session(
    interview_id: int,
    payload: SessionUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Updates the active assessment session state turn-by-turn for progress recovery.
    """
    service = InterviewService(db)
    try:
        updated = service.update_session_state(
            interview_id=interview_id,
            current_question_index=payload.current_question_index,
            session_state=payload.session_state,
            comfort_index=payload.comfort_index,
            raw_answers=payload.raw_answers,
            network_status=payload.network_status,
            completion_status=payload.completion_status,
        )
        return _build_response(updated)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{interview_id}/review", response_model=InterviewReportResponse)
def review_interview_report(
    interview_id: int,
    payload: InterviewReviewRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Allows a teacher/admin to review and edit evaluations/transcript details, and approve the report.
    """
    service = InterviewService(db)
    try:
        updated = service.review_and_approve_report(
            interview_id=interview_id,
            evaluated_answers=payload.evaluated_answers,
            admin_note=payload.admin_note,
            reviewed_by=current_user.get("name") or "Teacher"
        )
        return _build_response(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Helper to map SQLAlchemy model → Pydantic response ───────────────────────

def _build_response(iv) -> InterviewReportResponse:
    import json
    from sqlalchemy.orm import object_session
    
    # Load audio references safely
    audio_refs = []
    if iv.audio_references:
        try:
            audio_refs = json.loads(iv.audio_references) if isinstance(iv.audio_references, str) else iv.audio_references
        except Exception:
            audio_refs = []

    # Map evaluation steps safely
    steps_list = []
    if hasattr(iv, "evaluation_steps") and iv.evaluation_steps:
        for s in iv.evaluation_steps:
            steps_list.append({
                "step_name": s.step_name,
                "status": s.status,
                "output": s.output,
                "error": s.error,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None
            })

    # Build list of questions matching start_interview logic
    questions_list = []
    if iv.assessment:
        subject_name = iv.assessment.subject.name.lower() if iv.assessment.subject else ""
        default_skill = "communication"
        if "math" in subject_name or "num" in subject_name:
            default_skill = "numeracy"
        elif "art" in subject_name or "creat" in subject_name:
            default_skill = "creativity"
            
        db = object_session(iv)
        questions_to_use = []
        if db:
            from app.services.assessment_service import AssessmentService
            asmt_service = AssessmentService(db)
            token = iv.student_assessment.token if iv.student_assessment else None
            try:
                questions_to_use = asmt_service.get_questions_for_session(iv.assessment_id, seed_str=token)
            except Exception:
                questions_to_use = list(iv.assessment.questions) if iv.assessment.questions else []
        else:
            questions_to_use = list(iv.assessment.questions) if iv.assessment.questions else []

        for q in questions_to_use:
            hint_val = getattr(q, 'hint', None)
            if not hint_val:
                text_lower = q.text.lower()
                if "numerator" in text_lower:
                    hint_val = "In a fraction, the numerator is the number on the top, which tells us how many parts we are taking."
                elif "denominator" in text_lower:
                    hint_val = "In a fraction, the denominator is the bottom number, which tells us the total number of equal parts."
                elif "equivalent" in text_lower:
                    hint_val = "To find equivalent fractions, think about multiplying or dividing both top and bottom numbers by the same number."
                elif " राहुल" in text_lower or "rahul" in text_lower or "pizza" in text_lower:
                    hint_val = "Think about the total number of slices as the bottom number, and the slices eaten as the top number."
                elif "shaded" in text_lower or "visual" in text_lower or "circle" in text_lower:
                    hint_val = "Count how many parts are colored blue compared to the total number of parts in the shape."
                else:
                    hint_val = "Let's think together. Can you break the question down or explain what you think it means?"
            
            questions_list.append({
                "q": q.text,
                "skill": default_skill,
                "category": q.chapter.title if q.chapter else "Assessment Content",
                "hint": hint_val
            })
            
        # Fallback if no questions are assigned to the assessment
        if len(questions_list) == 0:
            questions_list.append({
                "q": "If you could visit any place in the world, where would you go and why?",
                "skill": "creativity",
                "category": "Aspirations"
            })

    return InterviewReportResponse(
        id=iv.id,
        student_name=iv.student_name,
        student_class=iv.student_class,
        assessment_title=iv.assessment.title if iv.assessment else None,
        questions=questions_list,
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
        transcript=json.loads(iv.transcript) if iv.transcript else [],
        language=iv.language,
        confidence=iv.confidence,
        audio_references=audio_refs,
        report_version=iv.report_version,
        evaluation_steps=steps_list,
        current_question_index=iv.current_question_index,
        session_state=iv.session_state,
        comfort_index=iv.comfort_index,
        raw_answers=iv.raw_answers,
        network_status=iv.network_status,
        completion_status=iv.completion_status,
        requires_review=iv.requires_review,
        review_reason=iv.review_reason,
        reviewed_by=iv.reviewed_by,
        reviewed_at=iv.reviewed_at,
        raw_transcript=iv.raw_transcript,
        clean_transcript=iv.clean_transcript,
        validated_transcript=iv.validated_transcript,
    )