import os
import json
import datetime
import shutil
from typing import Optional
from sqlalchemy.orm import Session

from app.models.interview import Interview, InterviewMessage, ConversationTurn
from app.services.interview_engine import InterviewEngine
from app.core.config import settings

class ConversationEngine:
    """
    ConversationEngine is responsible for managing every conversational turn during the interview.
    Input: student response, optional audio URL.
    Output: Next turn details (next speech, next state, metrics).
    Does NOT evaluate correctness or generate reports.
    """
    def __init__(self, db: Session):
        self.db = db
        self.interview_engine = InterviewEngine()

    def process_turn(self, interview_id: int, student_response: str, audio_url: Optional[str] = None) -> dict:
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")

        # Load session_state_data
        session_data = interview.session_state_data or {}
        if not session_data:
            session_data = self._initialize_fallback_session_data(interview)

        questions = session_data.get("questions") or []
        current_idx = session_data.get("current_question_index", 0)
        current_state = session_data.get("session_state", "meet_buddy")
        comfort_idx = session_data.get("comfort_index", 0)
        history = session_data.setdefault("history", [])

        # Save student turn in history
        history.append({"role": "student", "text": student_response, "state": current_state})

        # Find the last Buddy message that prompted this student response
        buddy_msg = ""
        # 1. Look in history
        for h in reversed(history[:-1]):  # exclude the student response we just appended
            if h.get("role") == "ai":
                buddy_msg = h.get("text")
                break
        # 2. Query DB as fallback
        if not buddy_msg:
            last_ai_msg = self.db.query(InterviewMessage).filter(
                InterviewMessage.interview_id == interview_id,
                InterviewMessage.role == "ai"
            ).order_by(InterviewMessage.id.desc()).first()
            if last_ai_msg:
                buddy_msg = last_ai_msg.text

        # Create structured ConversationTurn DB record
        conv_turn = ConversationTurn(
            interview_id=interview.id,
            question_id=str(current_idx),
            buddy_message=buddy_msg,
            student_transcript=student_response,
            audio_url=audio_url,
            created_at=datetime.datetime.utcnow()
        )
        self.db.add(conv_turn)

        # Save student message turn in InterviewMessage DB table for compatibility
        student_msg = InterviewMessage(
            interview_id=interview.id,
            role="student",
            text=student_response,
            question_category=current_state,
            sequence_number=len(history),
            student_response=student_response,
            audio_url=audio_url
        )
        self.db.add(student_msg)

        # Track raw answers
        raw_answers = session_data.setdefault("raw_answers", [])
        q = questions[current_idx] if current_idx < len(questions) else None
        if q and current_state in ["interview", "HINT", "FOLLOWUP"]:
            ans_exists = False
            for ans in raw_answers:
                if ans.get("question") == q.get("q") or ans.get("question") == q.get("text"):
                    ans["answer"] = ans.get("answer", "") + " | " + student_response
                    ans_exists = True
                    break
            if not ans_exists:
                raw_answers.append({
                    "question_category": q.get("skill", "General"),
                    "question": q.get("text") or q.get("q"),
                    "answer": student_response
                })

        # Decide next question/action via InterviewEngine
        persona = session_data.get("persona") or {}
        engine_result = self.interview_engine.process_interview_flow(
            questions=questions,
            current_idx=current_idx,
            current_state=current_state,
            comfort_idx=comfort_idx,
            hints_used=session_data.get("hints_used_count", 0),
            followups_used=session_data.get("followups_used_count", 0),
            student_response=student_response,
            persona=persona,
            student_name=interview.student_name
        )

        next_speech = engine_result["next_speech"]
        next_state = engine_result["next_state"]
        is_completed = engine_result["is_completed"]

        # Save Buddy message in history
        history.append({"role": "ai", "text": next_speech, "state": next_state})

        # Save Buddy message turn in InterviewMessage DB table for compatibility
        buddy_db_msg = InterviewMessage(
            interview_id=interview.id,
            role="ai",
            text=next_speech,
            question_category=next_state,
            sequence_number=len(history),
            buddy_response=next_speech
        )
        self.db.add(buddy_db_msg)

        # Update database values for session recovery
        session_data["session_state"] = next_state
        session_data["comfort_index"] = engine_result["comfort_index"]
        session_data["current_question_index"] = engine_result["current_question_index"]
        session_data["hints_used_count"] = engine_result["hints_used_count"]
        session_data["followups_used_count"] = engine_result["followups_used_count"]

        interview.current_question_index = engine_result["current_question_index"]
        interview.session_state = next_state
        interview.comfort_index = engine_result["comfort_index"]
        interview.raw_answers = raw_answers
        interview.session_state_data = session_data

        if is_completed:
            interview.completion_status = "Completed"
            interview.status = "Transcript Saved"
            interview.completed_at = datetime.datetime.utcnow()
            interview.transcript = json.dumps([{"role": h["role"], "text": h["text"]} for h in history])
            
            # Trigger asynchronous evaluation pipeline
            self._trigger_background_evaluation(interview)

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(interview, "session_state_data")

        self.db.commit()

        # Try to run cleanup asynchronously in a separate background thread
        # to ensure expired audio recordings are cleared periodically
        self._trigger_lazy_cleanup()

        # Map response matches
        q_hints = q.get("hints") or [] if q else []
        q_followups = q.get("followups") or [] if q else []
        
        return {
            "next_speech": next_speech,
            "next_state": next_state,
            "hints_remaining": max(0, len(q_hints) - engine_result["hints_used_count"]),
            "followups_remaining": max(0, len(q_followups) - engine_result["followups_used_count"]),
            "active_hint": engine_result["active_hint"],
            "questions": questions,
            "current_question_index": engine_result["current_question_index"],
            "comfort_index": engine_result["comfort_index"],
            "completion_status": interview.completion_status
        }

    def cleanup_expired_audio(self) -> int:
        """
        Finds all completed interviews older than 30 days and removes their audio recordings.
        """
        limit_date = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        expired_interviews = self.db.query(Interview).filter(
            Interview.completed_at <= limit_date,
            Interview.status == "Completed"
        ).all()

        cleaned_count = 0
        for iv in expired_interviews:
            folder = os.path.join("static", "interviews", str(iv.id))
            if os.path.exists(folder):
                try:
                    shutil.rmtree(folder)
                    cleaned_count += 1
                except Exception as e:
                    print(f"[ConversationEngine] Failed to delete audio folder {folder}: {e}", flush=True)

        return cleaned_count

    def _trigger_lazy_cleanup(self):
        """
        Trigger the cleanup of expired audio files in a daemon thread.
        """
        import threading
        def run_cleanup():
            from app.db.session import SessionLocal
            db = SessionLocal()
            try:
                engine = ConversationEngine(db)
                count = engine.cleanup_expired_audio()
                if count > 0:
                    print(f"[ConversationEngine] Cleaned up audio files for {count} expired interviews.", flush=True)
            except Exception as e:
                print(f"[ConversationEngine] Error in background audio cleanup: {e}", flush=True)
            finally:
                db.close()
        
        threading.Thread(target=run_cleanup, daemon=True).start()

    def _initialize_fallback_session_data(self, interview: Interview) -> dict:
        # Load questions to use if not present
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
            "history": []
        }

    def _trigger_background_evaluation(self, interview: Interview):
        try:
            # Check if Redis is alive before calling Celery
            redis_alive = False
            try:
                import redis
                r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=0.5, socket_connect_timeout=0.5)
                r.ping()
                redis_alive = True
            except Exception:
                redis_alive = False

            if redis_alive:
                from app.tasks.evaluation_tasks import evaluate_interview_task
                evaluate_interview_task.delay(interview.id)
                print(f"[ConversationEngine] Triggered asynchronous evaluation task via Celery for interview {interview.id}", flush=True)
            else:
                print(f"[ConversationEngine] Redis not reachable. Running pipeline synchronously in background thread.", flush=True)
                import threading
                from app.services.evaluation_pipeline import EvaluationPipelineService
                def run_sync():
                    from app.db.session import SessionLocal
                    db = SessionLocal()
                    try:
                        pipeline = EvaluationPipelineService(db)
                        pipeline.run_pipeline(interview.id)
                    except Exception as e:
                        print(f"Background thread evaluation failed: {e}", flush=True)
                    finally:
                        db.close()
                threading.Thread(target=run_sync).start()
        except Exception as e:
            print(f"[ConversationEngine] Failed to trigger background evaluation: {e}", flush=True)
