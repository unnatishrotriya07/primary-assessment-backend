"""Atomic, fail-closed interview turn engine (self-contained, LangGraph-free).

Replaces the legacy per-turn flow with:
  - row-level locking + a single commit (atomic turn, no half-written state)
  - fail-closed intent classification (never praise on LLM failure)
  - rollback to a neutral response on any unexpected error
Uses only shared infra (Interview model, Pydantic AI agents, Celery task).
"""
import datetime
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

import app.common.database  # noqa: F401  # registers all models + Base first (avoids circular import)

from app.core.models.interview import Interview, InterviewMessage, ConversationTurn
from app.core.models.student_assessment import StudentAssessment
from app.ai_interview.config import ai_interview_settings
from app.ai_interview.state import load_session, save_session
from app.ai_interview.intent import classify_intent
from app.ai_interview.planner import plan_action
from app.ai_interview.agents import build_welcome_speech, build_assessment_speech, build_goodbye_speech

logger = logging.getLogger(__name__)


class AiInterviewEngine:
    def __init__(self, db: Session):
        self.db = db

    # ── Public ────────────────────────────────────────────────────────────────
    def process_turn(self, interview_id: int, student_response: str, audio_url: Optional[str] = None) -> dict:
        # Row lock serializes concurrent turns for the same interview (idempotency).
        interview = (
            self.db.query(Interview)
            .filter(Interview.id == interview_id)
            .with_for_update()
            .first()
        )
        if not interview:
            raise ValueError("Interview not found.")

        state = load_session(self.db, interview)

        # Completed interviews are read-only no-ops.
        if state.get("completion_status") == "Completed":
            return self._build_response(interview, state, next_speech="", action="completed")

        student_response = (student_response or "").strip()

        try:
            return self._run_turn(interview, state, student_response, audio_url)
        except Exception as e:
            self.db.rollback()
            logger.error("[ai_interview] turn failed; rolling back to neutral response: %s", e, exc_info=True)
            # Fail-closed: do NOT advance state or praise; ask the child to retry.
            neutral = "Could you say that again? Take your time."
            return self._build_response(interview, load_session(self.db, interview), next_speech=neutral, action="encourage_retry")

    # ── Internals ─────────────────────────────────────────────────────────────
    def _run_turn(self, interview: Interview, state: dict, student_response: str, audio_url: Optional[str]) -> dict:
        self._record_student_turn(interview, state, student_response, audio_url)

        session_state = state.get("session_state", "meet_buddy")

        if session_state == "meet_buddy":
            return self._handle_meet(interview, state, student_response)
        if session_state == "comfort_conv":
            return self._handle_comfort(interview, state, student_response)
        if session_state == "GOODBYE":
            return self._build_response(interview, state, next_speech="", action="completed")

        # interview loop
        result = self._handle_interview(interview, state, student_response)
        self._commit(interview, state)
        return result

    def _handle_meet(self, interview: Interview, state: dict, student_response: str) -> dict:
        comfort_index = state.get("comfort_index", 0)
        if comfort_index == 0:
            # First contact: greet + ask how they are.
            next_speech = build_welcome_speech(
                comfort_index=0,
                student_name=state.get("student_name", interview.student_name),
                student_grade=state.get("student_class", interview.student_class),
                student_response="",
            )
            state["comfort_index"] = 1
            state["session_state"] = "comfort_conv"
        else:
            next_speech = "What did you enjoy doing today?"
            state["comfort_index"] = 2

        self._record_ai_turn(interview, state, next_speech)
        return self._build_response(interview, state, next_speech=next_speech, action="comfort")

    def _handle_comfort(self, interview: Interview, state: dict, student_response: str) -> dict:
        comfort_index = state.get("comfort_index", 1)
        if comfort_index < 2:
            next_speech = "Ready to learn together?"
            state["comfort_index"] = 2
        else:
            next_speech = build_welcome_speech(
                comfort_index=1,
                student_name=state.get("student_name", interview.student_name),
                student_grade=state.get("student_class", interview.student_class),
                student_response=student_response,
            )
            questions = state.get("questions") or []
            state["comfort_index"] = 3
            state["session_state"] = "interview"
            state["current_question_index"] = 0
            first_q = questions[0]["text"] if questions else None
            if first_q:
                next_speech = f"{next_speech} Let's start with our first question: {first_q}"
            else:
                return self._finish(interview, state, override_speech=next_speech)

        self._record_ai_turn(interview, state, next_speech)
        return self._build_response(interview, state, next_speech=next_speech, action="comfort")

    def _handle_interview(self, interview: Interview, state: dict, student_response: str) -> dict:
        questions = state.get("questions") or []
        idx = int(state.get("current_question_index", 0) or 0)
        q = questions[idx] if idx < len(questions) else None

        if q is None:
            return self._finish(interview, state)

        hints_used = int(state.get("hints_used_count", 0) or 0)
        silence_nudges = int(state.get("silence_nudges_count", 0) or 0)
        hints_limit = ai_interview_settings.AI_INTERVIEW_HINTS_LIMIT
        silence_limit = ai_interview_settings.AI_INTERVIEW_SILENCE_NUDGES_LIMIT

        intent_res = classify_intent(
            response=student_response,
            question_text=q.get("text", ""),
            expected_concepts=q.get("expected_concepts", []),
            provider=ai_interview_settings.AI_INTERVIEW_LLM_PROVIDER,
        )
        plan = plan_action(intent_res.intent, hints_used, hints_limit, silence_nudges, silence_limit)
        action = plan["action"]

        # Reset the silence counter on any real (non-silence) attempt.
        if intent_res.intent not in ("SILENCE", "UNKNOWN"):
            state["silence_nudges_count"] = 0

        next_question = None
        advance = plan.get("advance", False)

        if action == "repeat":
            next_speech = build_assessment_speech(
                action="repeat",
                student_name=state.get("student_name", interview.student_name),
                student_grade=state.get("student_class", interview.student_class),
                current_question=q.get("text", ""),
                student_response=student_response,
            ) + f" {q.get('text', '')}"
        elif action == "hint":
            hints_used += 1
            state["hints_used_count"] = hints_used
            hints = q.get("hints") or ["Try breaking the question down step by step."]
            active_hint = hints[min(hints_used - 1, len(hints) - 1)]
            next_speech = build_assessment_speech(
                action="hint",
                student_name=state.get("student_name", interview.student_name),
                student_grade=state.get("student_class", interview.student_class),
                current_question=q.get("text", ""),
                student_response=student_response,
                active_hint=active_hint,
            ) + f" {q.get('text', '')}"
        elif action == "encourage_topic":
            next_speech = build_assessment_speech(
                action="encourage_topic",
                student_name=state.get("student_name", interview.student_name),
                student_grade=state.get("student_class", interview.student_class),
                current_question=q.get("text", ""),
                student_response=student_response,
            ) + f" {q.get('text', '')}"
        elif action == "encourage_retry":
            state["silence_nudges_count"] = silence_nudges + 1
            next_speech = build_assessment_speech(
                action="encourage_retry",
                student_name=state.get("student_name", interview.student_name),
                student_grade=state.get("student_class", interview.student_class),
                current_question=q.get("text", ""),
                student_response=student_response,
            )
        elif action == "skip":
            next_question = self._next_question_text(questions, idx)
            next_speech = build_assessment_speech(
                action="skip",
                student_name=state.get("student_name", interview.student_name),
                student_grade=state.get("student_class", interview.student_class),
                current_question=q.get("text", ""),
                student_response=student_response,
                next_question=next_question,
            )
        elif action == "praise":
            next_question = self._next_question_text(questions, idx)
            next_speech = build_assessment_speech(
                action="praise",
                student_name=state.get("student_name", interview.student_name),
                student_grade=state.get("student_class", interview.student_class),
                current_question=q.get("text", ""),
                student_response=student_response,
                next_question=next_question,
            )
        else:  # unreachable, but fail-closed anyway
            next_speech = "Could you say that again? Take your time."
            action = "encourage_retry"

        if advance:
            idx += 1
            state["current_question_index"] = idx
            state["silence_nudges_count"] = 0
            if idx >= len(questions):
                return self._finish(interview, state, override_speech=next_speech)

        state.setdefault("active_hint", None)
        self._record_ai_turn(interview, state, next_speech)
        return self._build_response(interview, state, next_speech=next_speech, action=action)

    def _finish(self, interview: Interview, state: dict, override_speech: Optional[str] = None) -> dict:
        next_speech = override_speech or build_goodbye_speech(
            student_name=state.get("student_name", interview.student_name),
            student_grade=state.get("student_class", interview.student_class),
            history=state.get("history"),
        )
        state["session_state"] = "GOODBYE"
        state["completion_status"] = "Completed"
        self._record_ai_turn(interview, state, next_speech)

        interview.completion_status = "Completed"
        interview.status = "Transcript Saved"
        interview.completed_at = datetime.datetime.utcnow()
        interview.transcript = json.dumps([{"role": h["role"], "text": h["text"]} for h in state.get("history", [])])

        sa = self.db.query(StudentAssessment).filter(StudentAssessment.id == interview.student_assessment_id).first()
        if sa:
            sa.status = "Completed"

        self._commit(interview, state)
        self._trigger_evaluation(interview)
        return self._build_response(interview, state, next_speech=next_speech, action="goodbye")

    # ── persistence helpers ───────────────────────────────────────────────────
    def _record_student_turn(self, interview: Interview, state: dict, text: str, audio_url: Optional[str]) -> None:
        idx = int(state.get("current_question_index", 0) or 0)
        questions = state.get("questions") or []
        q_id = str(questions[idx].get("id")) if idx < len(questions) else str(idx)

        last_ai = ""
        for h in reversed(state.get("history", [])):
            if h.get("role") == "ai":
                last_ai = h.get("text", "")
                break

        self.db.add(ConversationTurn(
            interview_id=interview.id,
            question_id=q_id,
            buddy_message=last_ai,
            student_transcript=text,
            audio_url=audio_url,
        ))
        self.db.add(InterviewMessage(
            interview_id=interview.id,
            role="student",
            text=text,
            question_category=state.get("session_state", "interview"),
            sequence_number=len(state.get("history", [])) + 1,
            student_response=text,
            audio_url=audio_url,
        ))
        state.setdefault("history", []).append({"role": "student", "text": text, "question_category": state.get("session_state", "interview")})

    def _record_ai_turn(self, interview: Interview, state: dict, text: str) -> None:
        self.db.add(InterviewMessage(
            interview_id=interview.id,
            role="ai",
            text=text,
            question_category=state.get("session_state", "interview"),
            sequence_number=len(state.get("history", [])) + 1,
            buddy_response=text,
        ))
        state.setdefault("history", []).append({"role": "ai", "text": text, "question_category": state.get("session_state", "interview")})

    def _commit(self, interview: Interview, state: dict) -> None:
        save_session(self.db, interview, state)
        self.db.commit()
        self.db.refresh(interview)

    def _trigger_evaluation(self, interview: Interview) -> None:
        if not ai_interview_settings.AI_INTERVIEW_TRIGGER_EVALUATION:
            return
        try:
            import redis
            from app.core.config import settings
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=0.5, socket_connect_timeout=0.5)
            r.ping()
        except Exception as e:
            logger.warning("[ai_interview] Redis/Celery unavailable; evaluation can be triggered via regenerate later: %s", e)
            return
        try:
            from app.tasks.evaluation_tasks import evaluate_interview_task
            evaluate_interview_task.delay(interview.id)
            logger.info("[ai_interview] Enqueued evaluation for interview %s", interview.id)
        except Exception as e:
            logger.error("[ai_interview] Failed to enqueue evaluation: %s", e)

    # ── response helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _next_question_text(questions: list, idx: int) -> Optional[str]:
        if idx + 1 < len(questions):
            return questions[idx + 1].get("text")
        return None

    @staticmethod
    def _build_response(interview: Interview, state: dict, next_speech: str, action: str) -> dict:
        questions = state.get("questions") or []
        idx = int(state.get("current_question_index", 0) or 0)
        hints_used = int(state.get("hints_used_count", 0) or 0)
        q_hints = questions[idx].get("hints") or [] if idx < len(questions) else []
        hints_remaining = max(0, len(q_hints) - hints_used)

        return {
            "interview_id": interview.id,
            "next_speech": next_speech,
            "next_state": state.get("session_state", "meet_buddy"),
            "action": action,
            "current_question_index": idx,
            "comfort_index": int(state.get("comfort_index", 0) or 0),
            "hints_remaining": hints_remaining,
            "active_hint": state.get("active_hint"),
            "completion_status": state.get("completion_status", interview.completion_status or "In Progress"),
        }
