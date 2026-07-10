from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.chapter_service import ChapterService
import traceback

@celery_app.task(name="app.tasks.sync_tasks.sync_ncert_chapter_task", bind=True, max_retries=3)
def sync_ncert_chapter_task(self, chapter_id: int):
    print(f"[Celery Worker] Starting sync ncert task for chapter {chapter_id}, attempt: {self.request.retries}", flush=True)
    db = SessionLocal()
    try:
        service = ChapterService(db)
        # Call the sync function which has been updated to be S3-backed and async-safe
        service.sync_ncert_content(chapter_id)
        print(f"[Celery Worker] Successfully completed sync task for chapter {chapter_id}", flush=True)
        return {"status": "success", "chapter_id": chapter_id}
    except Exception as exc:
        db.rollback()
        print(f"[Celery Worker] Sync task failed for chapter {chapter_id}: {exc}", flush=True)
        traceback.print_exc()
        try:
            # Retry with exponential backoff (e.g. 5s, 10s, 20s)
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)
        except Exception as retry_exc:
            raise retry_exc
    finally:
        db.close()
