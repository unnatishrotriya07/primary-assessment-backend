from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.application import GenerateReportUseCase
import traceback

@celery_app.task(name="app.tasks.evaluation_tasks.evaluate_interview_task", bind=True, max_retries=3)
def evaluate_interview_task(self, interview_id: int):
    print(f"[Celery Worker] Starting evaluation task for interview {interview_id}, attempt: {self.request.retries}", flush=True)
    db = SessionLocal()
    try:
        use_case = GenerateReportUseCase(db)
        result = use_case.execute(interview_id)
        print(f"[Celery Worker] Successfully completed evaluation task for interview {interview_id}", flush=True)
        return result
    except Exception as exc:
        db.rollback()
        print(f"[Celery Worker] Task failed for interview {interview_id}: {exc}", flush=True)
        traceback.print_exc()
        try:
            # Retry with exponential backoff (e.g. 5s, 10s, 20s)
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)
        except Exception as retry_exc:
            # Re-raise retry exception or task error
            raise retry_exc
    finally:
        db.close()


@celery_app.task(name="app.tasks.evaluation_tasks.cleanup_expired_audio_task")
def cleanup_expired_audio_task():
    print("[Celery Worker] Starting periodic audio recordings cleanup task", flush=True)
    db = SessionLocal()
    try:
        from app.services.conversation_engine import ConversationEngine
        engine = ConversationEngine(db)
        cleaned_count = engine.cleanup_expired_audio()
        print(f"[Celery Worker] Successfully cleaned up {cleaned_count} expired interview audio directories", flush=True)
        return cleaned_count
    except Exception as exc:
        db.rollback()
        print(f"[Celery Worker] Audio cleanup task failed: {exc}", flush=True)
        traceback.print_exc()
        raise exc
    finally:
        db.close()
