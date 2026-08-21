import datetime
import pytest
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine, Base
from app.core.models.interview import Interview, InterviewMessage, ConversationTurn

from app.ai_interview.intent import classify_intent, IntentResult
from app.ai_interview.planner import plan_action
from app.ai_interview.engine import AiInterviewEngine
from app.ai_interview import intent as intent_mod
from app.ai_interview.agents import IntentOutput


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _failing_agent(monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("LLM provider down")
    monkeypatch.setattr(intent_mod.agents, "classify", _boom)


# ── Fail-closed intent ────────────────────────────────────────────────────────
def test_intent_fail_closed_on_llm_error(monkeypatch):
    _failing_agent(monkeypatch)
    res = classify_intent("I think the answer is three", "What is 2+1?", [])
    assert res.intent == "UNKNOWN"
    assert res.intent != "RESONATES_ANSWER"


def test_intent_never_praise_on_error(monkeypatch):
    _failing_agent(monkeypatch)
    res = classify_intent("some answer", "Question?", [])
    plan = plan_action(res.intent, hints_used=0, hints_limit=2, silence_nudges=0, silence_nudges_limit=3)
    assert plan["action"] != "praise"
    assert plan["advance"] is False


def test_intent_heuristic_skip_keywords():
    res = classify_intent("skip this question", "Q?", [])
    assert res.intent == "SKIP"


def test_intent_uses_agent_output_when_valid(monkeypatch):
    monkeypatch.setattr(
        intent_mod.agents, "classify",
        lambda *a, **k: IntentOutput(intent="RESONATES_ANSWER", reason="on track", confidence=0.9),
    )
    res = classify_intent("two plus two is four", "What is 2+2?", ["four"])
    assert res.intent == "RESONATES_ANSWER"
    assert res.from_llm is True


# ── Planner ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("intent", ["UNKNOWN", "SILENCE", "I_DONT_KNOW", "CONFUSED", "OFF_TOPIC", "INCORRECT_ANSWER"])
def test_planner_neutral_for_ambiguous_intents(intent):
    plan = plan_action(intent, hints_used=0, hints_limit=2, silence_nudges=0, silence_nudges_limit=3)
    assert plan["action"] != "praise"


def test_planner_praise_only_on_positive_evidence():
    plan = plan_action("RESONATES_ANSWER", hints_used=0, hints_limit=2, silence_nudges=0, silence_nudges_limit=3)
    assert plan["action"] == "praise"
    assert plan["advance"] is True


def test_planner_silence_auto_skip_is_neutral():
    plan = plan_action("SILENCE", hints_used=0, hints_limit=2, silence_nudges=3, silence_nudges_limit=3)
    assert plan["action"] == "skip"
    assert plan["action"] != "praise"


# ── Engine ────────────────────────────────────────────────────────────────────
def _make_interview(db: Session, session_data: dict) -> Interview:
    iv = Interview(
        student_assessment_id=1,
        assessment_id=1,
        student_name="Test Student",
        student_class="Grade 4",
        status="In Progress",
        session_state="interview",
        session_state_data=session_data,
        current_question_index=0,
    )
    db.add(iv)
    db.commit()
    db.refresh(iv)
    return iv


_SESSION = {
    "student_name": "Test Student",
    "student_class": "Grade 4",
    "session_state": "interview",
    "current_question_index": 0,
    "comfort_index": 3,
    "hints_used_count": 0,
    "silence_nudges_count": 0,
    "questions": [
        {"id": 1, "text": "What is 2 + 2?", "hints": ["Count on your fingers."], "expected_concepts": ["four"], "skill": "numeracy"},
        {"id": 2, "text": "What is 5 x 5?", "hints": [], "expected_concepts": ["twenty-five"], "skill": "numeracy"},
    ],
    "history": [],
}


def test_engine_fails_closed_on_conversation_error(db_session, monkeypatch):
    iv = _make_interview(db_session, dict(_SESSION))
    engine = AiInterviewEngine(db_session)

    import app.ai_interview.engine as engine_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("speech gen failed")

    monkeypatch.setattr(engine_mod, "classify_intent", lambda **k: IntentResult("UNKNOWN", "test", from_llm=True))
    monkeypatch.setattr(engine_mod, "build_assessment_speech", _boom)

    result = engine.process_turn(iv.id, "four")
    assert result["action"] == "encourage_retry"
    assert "again" in result["next_speech"].lower()
    # Atomic: nothing from this failed turn persisted.
    assert db_session.query(InterviewMessage).filter(InterviewMessage.interview_id == iv.id).count() == 0
    assert db_session.query(ConversationTurn).filter(ConversationTurn.interview_id == iv.id).count() == 0


def test_engine_advances_on_positive_answer(db_session, monkeypatch):
    iv = _make_interview(db_session, dict(_SESSION))
    engine = AiInterviewEngine(db_session)

    import app.ai_interview.engine as engine_mod

    monkeypatch.setattr(engine_mod, "classify_intent", lambda **k: IntentResult("RESONATES_ANSWER", "test", from_llm=True))
    monkeypatch.setattr(engine_mod, "build_assessment_speech", lambda **k: "Great job!")

    result = engine.process_turn(iv.id, "four")
    assert result["action"] == "praise"
    assert result["current_question_index"] == 1
    # Both student + ai messages persisted atomically.
    msgs = db_session.query(InterviewMessage).filter(InterviewMessage.interview_id == iv.id).order_by(InterviewMessage.id).all()
    assert len(msgs) == 2
    assert msgs[0].role == "student"
    assert msgs[1].role == "ai"
    iv2 = db_session.query(Interview).filter(Interview.id == iv.id).first()
    assert iv2.current_question_index == 1


def test_engine_completes_and_marks_transcript_saved(db_session, monkeypatch):
    data = dict(_SESSION)
    data["current_question_index"] = 1  # on the last question
    iv = _make_interview(db_session, data)
    engine = AiInterviewEngine(db_session)

    import app.ai_interview.engine as engine_mod

    monkeypatch.setattr(engine_mod, "classify_intent", lambda **k: IntentResult("RESONATES_ANSWER", "test", from_llm=True))
    monkeypatch.setattr(engine_mod, "build_assessment_speech", lambda **k: "Well done!")
    monkeypatch.setattr(engine_mod.ai_interview_settings, "AI_INTERVIEW_TRIGGER_EVALUATION", False)

    result = engine.process_turn(iv.id, "twenty five")
    assert result["completion_status"] == "Completed"
    iv2 = db_session.query(Interview).filter(Interview.id == iv.id).first()
    assert iv2.status == "Transcript Saved"
    assert iv2.completion_status == "Completed"
    assert iv2.completed_at is not None
    assert iv2.session_state == "GOODBYE"
