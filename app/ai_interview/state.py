"""Session-state helpers for the ai_interview engine (reads/writes existing Interview row)."""
import json
from typing import Any, Dict, List

from sqlalchemy.orm import Session

import app.common.database  # noqa: F401  # registers models + Base first (avoids circular import)

from app.core.models.interview import Interview


def default_session_data(interview: Interview, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "student_name": interview.student_name,
        "student_class": interview.student_class,
        "current_question_index": 0,
        "comfort_index": 0,
        "hints_used_count": 0,
        "silence_nudges_count": 0,
        "questions": questions,
        "history": [],
    }


def parse_questions(interview: Interview, db: Session) -> List[Dict[str, Any]]:
    """Build question dicts from the existing assessment when session data is absent."""
    questions: List[Dict[str, Any]] = []
    if interview.assessment:
        for q in interview.assessment.questions:
            hints = []
            if getattr(q, "hints", None):
                try:
                    hints = json.loads(q.hints) if isinstance(q.hints, str) else list(q.hints or [])
                except Exception:
                    hints = []
            if not hints:
                hints = ["Try breaking the question down step by step."]
            questions.append({
                "id": getattr(q, "id", 0),
                "text": getattr(q, "text", ""),
                "skill": getattr(q, "skill", "communication"),
                "category": q.chapter.title if getattr(q, "chapter", None) else "Assessment Content",
                "hints": hints,
                "expected_concepts": getattr(q, "expected_concepts", []) or [],
                "followups": getattr(q, "followups", []) or [],
            })
    return questions


def load_session(db: Session, interview: Interview) -> Dict[str, Any]:
    """Load mutable session state from the interview row (lock-free; caller locks)."""
    raw = interview.session_state_data
    if raw:
        try:
            data = dict(raw) if isinstance(raw, dict) else json.loads(raw)
        except Exception:
            data = {}
    else:
        data = {}

    if not data.get("questions"):
        data["questions"] = parse_questions(interview, db)
    data.setdefault("current_question_index", interview.current_question_index or 0)
    data.setdefault("comfort_index", interview.comfort_index or 0)
    data.setdefault("hints_used_count", 0)
    data.setdefault("silence_nudges_count", 0)
    data.setdefault("student_name", interview.student_name)
    data.setdefault("student_class", interview.student_class)
    data.setdefault("history", [])
    return data


def save_session(db: Session, interview: Interview, data: Dict[str, Any]) -> None:
    """Persist session state and the mirrored top-level columns (no commit here)."""
    interview.session_state_data = data
    interview.current_question_index = int(data.get("current_question_index", 0) or 0)
    interview.comfort_index = int(data.get("comfort_index", 0) or 0)
    interview.session_state = data.get("session_state", interview.session_state or "meet_buddy")
    interview.completion_status = data.get("completion_status", interview.completion_status or "In Progress")
