import logging
import traceback

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.application import GenerateReportUseCase

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.evaluation_tasks.evaluate_interview_task",
    bind=True,
    max_retries=3,
)
def evaluate_interview_task(self, interview_id: int):
    logger.info("Starting evaluation task", extra={"interview_id": interview_id, "attempt": self.request.retries + 1})
    db = SessionLocal()
    try:
        use_case = GenerateReportUseCase(db)
        result = use_case.execute(interview_id)
        logger.info("Completed evaluation task", extra={"interview_id": interview_id})
        return result
    except Exception as exc:
        db.rollback()
        logger.exception("Evaluation task failed", extra={"interview_id": interview_id})
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)
        except Exception as retry_exc:
            raise retry_exc
    finally:
        db.close()


@celery_app.task(name="app.tasks.evaluation_tasks.cleanup_expired_audio_task")
def cleanup_expired_audio_task():
    logger.info("Starting periodic audio recordings cleanup task")
    db = SessionLocal()
    try:
        from app.services.conversation_engine import ConversationEngine
        engine = ConversationEngine(db)
        cleaned_count = engine.cleanup_expired_audio()
        logger.info("Audio cleanup finished", extra={"cleaned_count": cleaned_count})
        return cleaned_count
    except Exception as exc:
        db.rollback()
        logger.exception("Audio cleanup task failed")
        raise exc
    finally:
        db.close()
