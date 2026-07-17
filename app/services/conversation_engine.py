import os
import json
import datetime
import shutil
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.interview import Interview, InterviewMessage, ConversationTurn
from app.core.config import settings

logger = logging.getLogger(__name__)

class ConversationEngine:
    """
    ConversationEngine is responsible for managing every conversational turn during the interview.
    Input: student response, optional audio URL.
    Output: Next turn details (next speech, next state, metrics).
    Does NOT evaluate correctness or generate reports.
    """
    def __init__(self, db: Session):
        self.db = db

    def process_turn(self, interview_id: int, student_response: str, audio_url: Optional[str] = None) -> dict:
        from app.ai_assessment.interview.session_manager import SessionManager
        from app.ai_assessment.interview.graph import interview_graph

        session_mgr = SessionManager(self.db)
        
        # Load state dict from postgresql
        state = session_mgr.load_session(interview_id)
        
        # Update dynamic turn inputs
        state["student_response"] = student_response
        state["audio_url"] = audio_url

        # Check for last buddy message to write structured turn row
        last_ai_text = ""
        for h in reversed(state["transcript"]):
            if h.get("role") == "ai":
                last_ai_text = h.get("text", "")
                break

        # Save student turn DB records
        q_idx = state["current_question_index"]
        questions = state["questions"]
        q_id_str = str(questions[q_idx].get("id")) if q_idx < len(questions) else str(q_idx)

        session_mgr.add_conversation_turn(
            interview_id=interview_id,
            question_id=q_id_str,
            buddy_message=last_ai_text,
            student_transcript=student_response,
            audio_url=audio_url
        )

        session_mgr.add_message(
            interview_id=interview_id,
            role="student",
            text=student_response,
            question_category=state["session_state"],
            sequence_number=len(state["transcript"]) + 1,
            student_response=student_response,
            audio_url=audio_url
        )

        # Execute LangGraph state machine
        logger.info(f"[ConversationEngine] Running LangGraph for interview {interview_id}")
        result_state = interview_graph.invoke(state)

        # Update Session with the resulting speech message
        next_speech = result_state["next_speech"]
        next_state = result_state["session_state"]
        
        session_mgr.add_message(
            interview_id=interview_id,
            role="ai",
            text=next_speech,
            question_category=next_state,
            sequence_number=len(result_state["transcript"]),
            buddy_response=next_speech
        )

        # Save session variables back to postgresql
        session_mgr.save_session(interview_id, result_state)

        # Check completed trigger
        if result_state["completion_status"] == "Completed":
            # Sync final interview fields
            interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
            if interview:
                interview.completion_status = "Completed"
                interview.status = "Transcript Saved"
                interview.completed_at = datetime.datetime.utcnow()
                interview.transcript = json.dumps([{"role": h["role"], "text": h["text"]} for h in result_state["transcript"]])
                
                # Update student assessment status to Completed
                from app.core.models.student_assessment import StudentAssessment
                sa = self.db.query(StudentAssessment).filter(StudentAssessment.id == interview.student_assessment_id).first()
                if sa:
                    sa.status = "Completed"
                
                self.db.commit()
                self._trigger_background_evaluation(interview)

        self._trigger_lazy_cleanup()

        # Calculate remaining hints
        q_hints = []
        if q_idx < len(questions):
            q_hints = questions[q_idx].get("hints") or []
        hints_remaining = max(0, len(q_hints) - result_state["hints_used_count"])

        return {
            "next_speech": next_speech,
            "next_state": next_state,
            "hints_remaining": hints_remaining,
            "followups_remaining": 0,  # Deprecated in V2
            "active_hint": result_state["active_hint"],
            "questions": questions,
            "current_question_index": result_state["current_question_index"],
            "comfort_index": result_state["comfort_index"],
            "completion_status": result_state["completion_status"]
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
                from app.application import GenerateReportUseCase
                def run_sync():
                    from app.db.session import SessionLocal
                    db = SessionLocal()
                    try:
                        use_case = GenerateReportUseCase(db)
                        use_case.execute(interview.id)
                    except Exception as e:
                        print(f"Background thread evaluation failed: {e}", flush=True)
                    finally:
                        db.close()
                threading.Thread(target=run_sync).start()
        except Exception as e:
            print(f"[ConversationEngine] Failed to trigger background evaluation: {e}", flush=True)
