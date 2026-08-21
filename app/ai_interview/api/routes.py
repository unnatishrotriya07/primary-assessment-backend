import json
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from sqlalchemy.orm import Session

import app.common.database  # noqa: F401  # registers models + Base first (avoids circular import)

from app.core.dependencies import get_db
from app.core.models.interview import Interview
from app.services.interview_service import InterviewService

from app.ai_interview.auth import require_interview_access, verify_token
from app.ai_interview.engine import AiInterviewEngine
from app.ai_interview.schemas import (
    AiHealthResponse,
    AiSessionResponse,
    AiStartRequest,
    AiStartResponse,
    AiSTTResponse,
    AiTTSRequest,
    AiTurnRequest,
    AiTurnResponse,
)
from app.ai_interview.speech.stt import get_stt_provider
from app.ai_interview.speech.tts import get_tts_provider

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Health ────────────────────────────────────────────────────────────────────
@router.get("/health", response_model=AiHealthResponse, tags=["ai-interviews"])
async def ai_voice_health():
    try:
        stt = get_stt_provider()
        stt_ok = stt.is_configured()
    except Exception:
        stt_ok = False
    try:
        tts = get_tts_provider()
        tts_ok = tts.is_configured()
    except Exception:
        tts_ok = False
    return AiHealthResponse(
        status="ok" if (stt_ok and tts_ok) else "degraded",
        stt="available" if stt_ok else "unavailable",
        tts="available" if tts_ok else "unavailable",
    )


# ── Start ─────────────────────────────────────────────────────────────────────
@router.post("/start", response_model=AiStartResponse, tags=["ai-interviews"])
async def ai_start_interview(payload: AiStartRequest, db: Session = Depends(get_db)):
    """Token + email gated start. Delegates question compilation to the existing engine."""
    # Validates token + email (raises 401 on failure).
    verify_token(db, payload.token, payload.email)
    try:
        result = InterviewService(db).start_interview(payload.token, payload.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return AiStartResponse(
        interview_id=result.get("interview_id"),
        student_name=result.get("student_name", ""),
        student_class=result.get("student_class", ""),
        assessment_title=result.get("assessment_title"),
        questions=result.get("questions") or [],
        subject_name=result.get("subject_name"),
    )


# ── Turn ──────────────────────────────────────────────────────────────────────
@router.post("/{interview_id}/turn", response_model=AiTurnResponse, tags=["ai-interviews"])
async def ai_turn(
    interview_id: int,
    payload: AiTurnRequest,
    interview: Interview = Depends(require_interview_access),
    db: Session = Depends(get_db),
):
    """Run the fail-closed engine off the event loop (short-lived DB session per request)."""
    try:
        result = await run_in_threadpool(_run_turn_sync, db, interview_id, payload.student_response, payload.audio_url)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AiTurnResponse(**result)


def _run_turn_sync(db: Session, interview_id: int, student_response: str, audio_url) -> dict:
    engine = AiInterviewEngine(db)
    return engine.process_turn(interview_id, student_response, audio_url)


# ── Session / report (token-gated) ───────────────────────────────────────────
@router.get("/{interview_id}", response_model=AiSessionResponse, tags=["ai-interviews"])
async def ai_get_session(
    interview_id: int,
    interview: Interview = Depends(require_interview_access),
):
    transcript = []
    if interview.transcript:
        try:
            transcript = json.loads(interview.transcript)
        except Exception:
            transcript = []
    return AiSessionResponse(
        interview_id=interview.id,
        student_name=interview.student_name,
        student_class=interview.student_class,
        session_state=interview.session_state or "meet_buddy",
        current_question_index=interview.current_question_index or 0,
        comfort_index=interview.comfort_index or 0,
        completion_status=interview.completion_status or "In Progress",
        status=interview.status or "In Progress",
        transcript=transcript,
    )


# ── Speech endpoints (real STT / TTS) ─────────────────────────────────────────
@router.post("/speech/stt", response_model=AiSTTResponse, tags=["ai-interviews"])
async def ai_stt(file: UploadFile = File(...)):
    provider = get_stt_provider()
    if not provider.is_configured():
        raise HTTPException(status_code=503, detail="STT provider is not configured.")
    content = await file.read()
    result = await provider.transcribe(
        content,
        filename=file.filename or "speech.webm",
        content_type=file.content_type or "audio/webm",
    )
    if result.error:
        raise HTTPException(status_code=502, detail=result.error)
    return AiSTTResponse(text=result.text, language=result.language, confidence=result.confidence, duration=result.duration)


@router.post("/speech/tts", tags=["ai-interviews"])
async def ai_tts(payload: AiTTSRequest):
    provider = get_tts_provider()
    if not provider.is_configured():
        raise HTTPException(status_code=503, detail="TTS provider is not configured.")
    try:
        audio = await provider.synthesize(payload.text, voice=payload.voice, speed=payload.speed)
    except Exception as e:
        logger.error("[ai_interview] TTS synthesis failed: %s", e)
        raise HTTPException(status_code=502, detail="TTS synthesis failed.")
    return Response(content=audio, media_type="audio/mpeg")
