"""
Dispatch interview evaluation to Celery — with a production-safe fallback policy.

In dev (APP_ENV=development) the in-process BackgroundTasks fallback is allowed so a
zero-Redis local setup still works. On staging/production there is NO fallback: if the
task cannot be enqueued we raise so the caller returns a 5xx rather than silently
double-running the pipeline on every API replica.
"""
import logging

from app.common.config import settings

logger = logging.getLogger(__name__)


def enqueue_evaluation(interview_id: int, service=None, background_tasks=None) -> None:
    """Enqueue evaluation for `interview_id`.

    `service` + `background_tasks` are only used for the dev-only in-process fallback.
    """
    from app.tasks.evaluation_tasks import evaluate_interview_task

    try:
        evaluate_interview_task.delay(interview_id)
        logger.info("Enqueued evaluation task for interview %s via Celery", interview_id)
        return
    except Exception as exc:
        if settings.is_production_like:
            logger.exception(
                "Celery enqueue failed for interview %s; no in-process fallback allowed", interview_id
            )
            raise RuntimeError(f"Failed to enqueue evaluation: {exc}") from exc

        if service is None or background_tasks is None:
            raise RuntimeError(f"Celery enqueue failed and no dev fallback provided: {exc}") from exc

        logger.warning(
            "Celery enqueue failed (%s); falling back to in-process BackgroundTasks (dev only).",
            exc,
        )
        background_tasks.add_task(service.evaluate_interview_in_background_v2, interview_id)
