import json
from sqlalchemy.orm import Session
from app.core.models.interview import Interview, InterviewMessage, ConversationTurn

class StateManager:
    def __init__(self, db: Session):
        self.db = db

    def update_session_state(
        self,
        interview_id: int,
        current_question_index: int,
        session_state: str,
        comfort_index: int,
        raw_answers: list = None,
        network_status: str = "online",
        completion_status: str = "In Progress",
    ) -> Interview:
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError("Interview session not found.")
        
        interview.current_question_index = current_question_index
        interview.session_state = session_state
        interview.comfort_index = comfort_index
        if raw_answers is not None:
            interview.raw_answers = raw_answers
        interview.network_status = network_status
        interview.completion_status = completion_status
        
        self.db.commit()
        self.db.refresh(interview)
        return interview

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
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError("Interview session not found.")
        
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
        self.db.refresh(msg)

        # Re-build progressive raw_transcript turn list
        messages = (
            self.db.query(InterviewMessage)
            .filter(InterviewMessage.interview_id == interview_id)
            .order_by(InterviewMessage.id.asc())
            .all()
        )
        raw_list = []
        for m in messages:
            raw_list.append({
                "role": m.role,
                "text": m.text,
                "category": m.question_category,
                "sequence_number": m.sequence_number,
                "speech_confidence": m.speech_confidence,
            })
        interview.raw_transcript = json.dumps(raw_list)
        self.db.commit()
        return msg
