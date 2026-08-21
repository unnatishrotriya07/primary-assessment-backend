from celery import Celery
from app.common.config import settings
from app.infrastructure.logging import setup_logging

setup_logging()

celery_app = Celery(
    "momentum_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
