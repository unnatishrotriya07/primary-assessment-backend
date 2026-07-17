import json
import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.core.models.interview import Interview, InterviewMessage, ConversationTurn

class SessionManager:
    """
    SessionManager is responsible for loading and persisting the interview session
    state in PostgreSQL, keeping the conversation graph stateless.
    """
    def __init__(self, db: Session):
        self.db = db

    def load_session(self, interview_id: int) -> Dict[str, Any]:
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")

        session_data = interview.session_state_data or {}
        if not session_data:
            session_data = self._initialize_fallback_session_data(interview)

        return {
            "interview_id": interview.id,
            "student_name": interview.student_name,
            "student_class": interview.student_class,
            "current_question_index": session_data.get("current_question_index", 0),
            "session_state": session_data.get("session_state", "meet_buddy"),
            "comfort_index": session_data.get("comfort_index", 0),
            "questions": session_data.get("questions") or [],
            "transcript": session_data.get("history") or [],
            "raw_answers": session_data.get("raw_answers") or [],
            "hints_used_count": session_data.get("hints_used_count", 0),
            "followups_used_count": session_data.get("followups_used_count", 0),
            "completion_status": interview.completion_status,
            "active_hint": session_data.get("active_hint", None),
            "student_response": "",
            "audio_url": None,
            "next_speech": "",
            "intent": "",
            "metrics": session_data.get("metrics") or {
                "hesitation_time": 0,
                "retries": 0,
                "skipped_questions": 0,
                "failures": 0,
                "start_time": datetime.datetime.utcnow().isoformat()
            }
        }

    def save_session(self, interview_id: int, state: Dict[str, Any]):
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")

        # Sync db columns
        interview.current_question_index = state["current_question_index"]
        interview.session_state = state["session_state"]
        interview.comfort_index = state["comfort_index"]
        interview.raw_answers = state["raw_answers"]
        interview.completion_status = state["completion_status"]

        # Sync session_state_data JSON
        session_data = interview.session_state_data or {}
        session_data["current_question_index"] = state["current_question_index"]
        session_data["session_state"] = state["session_state"]
        session_data["comfort_index"] = state["comfort_index"]
        session_data["history"] = state["transcript"]
        session_data["raw_answers"] = state["raw_answers"]
        session_data["hints_used_count"] = state["hints_used_count"]
        session_data["followups_used_count"] = state["followups_used_count"]
        session_data["active_hint"] = state["active_hint"]
        session_data["metrics"] = state["metrics"]
        interview.session_state_data = session_data

        flag_modified(interview, "session_state_data")
        flag_modified(interview, "raw_answers")
        self.db.commit()

    def add_message(
        self,
        interview_id: int,
        role: str,
        text: str,
        question_category: str = None,
        sequence_number: int = None,
        question_id: int = None,
        student_response: str = None,
        buddy_response: str = None,
        audio_url: str = None,
        speech_confidence: float = None,
    ) -> InterviewMessage:
        msg = InterviewMessage(
            interview_id=interview_id,
            role=role,
            text=text,
            question_category=question_category,
            sequence_number=sequence_number,
            question_id=question_id,
            student_response=student_response,
            buddy_response=buddy_response,
            audio_url=audio_url,
            speech_confidence=speech_confidence,
        )
        self.db.add(msg)
        self.db.commit()
        return msg

    def add_conversation_turn(
        self,
        interview_id: int,
        question_id: str,
        buddy_message: str,
        student_transcript: str,
        audio_url: str = None
    ) -> ConversationTurn:
        turn = ConversationTurn(
            interview_id=interview_id,
            question_id=question_id,
            buddy_message=buddy_message,
            student_transcript=student_transcript,
            audio_url=audio_url,
            created_at=datetime.datetime.utcnow()
        )
        self.db.add(turn)
        self.db.commit()
        return turn

    def _initialize_fallback_session_data(self, interview: Interview) -> Dict[str, Any]:
        from app.services.interview_service import get_basic_class_questions
        fallback_qs = get_basic_class_questions(interview.student_class)
        questions = []
        for idx, q in enumerate(fallback_qs):
            questions.append({
                "id": idx + 1,
                "q": q["q"],
                "skill": q["skill"],
                "category": q["category"],
                "hints": ["Let's try breaking it down."],
                "expected_concepts": [],
                "followups": []
            })
        return {
            "session_state": "meet_buddy",
            "current_question_index": 0,
            "comfort_index": 0,
            "hints_used_count": 0,
            "followups_used_count": 0,
            "hints_limit": 2,
            "followups_limit": 2,
            "questions": questions,
            "history": [],
            "raw_answers": [],
            "metrics": {
                "hesitation_time": 0,
                "retries": 0,
                "skipped_questions": 0,
                "failures": 0,
                "start_time": datetime.datetime.utcnow().isoformat()
            }
        }
