"""
Structured (JSON) logging setup.

Emits one JSON object per line so CloudWatch / any log aggregator can parse events:
    {"ts": "...", "level": "INFO", "logger": "app.tasks.evaluation_tasks",
     "env": "staging", "service": "api", "message": "...", "interview_id": 12, ...}

Importing this module configures the root logger once. Call `setup_logging()` explicitly
from entrypoints (main.py / worker) so `print()`-heavy legacy code can be migrated to
`logger.info(...)` with consistent output.
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone

from app.common.config import settings

_ENV = getattr(settings, "APP_ENV", "development")
_SERVICE = os.getenv("SERVICE_NAME", "api")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "env": _ENV,
            "service": _SERVICE,
            "message": record.getMessage(),
        }
        # Merge structured extras attached via logger.info("...", extra={"interview_id": 1})
        for key in ("interview_id", "step", "task_id", "interview", "duration_ms", "error"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: str | None = None) -> None:
    level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Keep third-party libraries quieter.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)


# Call once at import so any logger.info() before explicit setup still formats correctly.
setup_logging()
