import os
import sys
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Momentum API"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-in-production-12345")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
    
    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:4000"]
    
    # Gemini AI configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # OpenAI configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Groq configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Celery & Redis
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # SendGrid configuration
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL: str = os.getenv("SENDGRID_FROM_EMAIL", "")
    SKIP_EMAIL: str = os.getenv("SKIP_EMAIL", "true")

    # AWS S3 Configurations
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_STORAGE_BUCKET_NAME: str = os.getenv("AWS_STORAGE_BUCKET_NAME", "student-assessment-pictures-primary")

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

    def __init__(self, **values):
        if "BACKEND_CORS_ORIGINS" in os.environ:
            raw_origins = os.environ["BACKEND_CORS_ORIGINS"].strip()
            import json
            try:
                parsed = json.loads(raw_origins)
                if not isinstance(parsed, list):
                    os.environ["BACKEND_CORS_ORIGINS"] = json.dumps([str(parsed)])
            except json.JSONDecodeError:
                origins_list = [o.strip() for o in raw_origins.split(",") if o.strip()]
                os.environ["BACKEND_CORS_ORIGINS"] = json.dumps(origins_list)
        super().__init__(**values)
        _is_testing = (
            "unittest" in sys.modules or 
            "pytest" in sys.modules or 
            any(os.path.basename(arg) in ["pytest", "py.test"] for arg in sys.argv) or
            any(os.path.basename(arg).startswith("test_") for arg in sys.argv)
        )
        if _is_testing:
            self.DATABASE_URL = "sqlite:///./test.db"

settings = Settings()
