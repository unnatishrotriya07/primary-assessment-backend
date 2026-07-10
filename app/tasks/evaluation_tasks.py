from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.evaluation_pipeline import EvaluationPipelineService
import traceback

@celery_app.task(name="app.tasks.evaluation_tasks.evaluate_interview_task", bind=True, max_retries=3)
def evaluate_interview_task(self, interview_id: int):
    print(f"[Celery Worker] Starting evaluation task for interview {interview_id}, attempt: {self.request.retries}", flush=True)
    db = SessionLocal()
    try:
        pipeline = EvaluationPipelineService(db)
        result = pipeline.run_pipeline(interview_id)
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
