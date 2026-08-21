import os
from pydantic_settings import BaseSettings
from typing import Optional


class AiInterviewSettings(BaseSettings):
    """Configuration for the ai_interview module (self-contained, non-breaking)."""

    # LLM / intent
    AI_INTERVIEW_LLM_PROVIDER: str = os.getenv("AI_INTERVIEW_LLM_PROVIDER", "gemini")

    # Pydantic AI agents (model routing)
    AI_INTERVIEW_MODEL_PROVIDER: str = os.getenv("AI_INTERVIEW_MODEL_PROVIDER", "groq")
    AI_INTERVIEW_GROQ_MODEL: str = os.getenv("AI_INTERVIEW_GROQ_MODEL", "llama-3.3-70b-versatile")
    AI_INTERVIEW_GEMINI_MODEL: str = os.getenv("AI_INTERVIEW_GEMINI_MODEL", "gemini-2.0-flash")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GEMINI_OPENAI_BASE_URL: str = os.getenv("GEMINI_OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

    # STT (cloud)
    AI_INTERVIEW_STT_PROVIDER: str = os.getenv("AI_INTERVIEW_STT_PROVIDER", "groq")
    GROQ_STT_MODEL: str = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
    GROQ_STT_BASE_URL: str = os.getenv("GROQ_STT_BASE_URL", "https://api.groq.com/openai/v1")

    # TTS (cloud)
    AI_INTERVIEW_TTS_PROVIDER: str = os.getenv("AI_INTERVIEW_TTS_PROVIDER", "elevenlabs")
    ELEVENLABS_TTS_URL: str = os.getenv("ELEVENLABS_TTS_URL", "https://api.elevenlabs.io/v1/text-to-speech")
    ELEVENLABS_DEFAULT_VOICE: str = os.getenv("ELEVENLABS_DEFAULT_VOICE", "pNInz6obpgDQGcFmaJgB")
    KOKORO_BASE_URL: str = os.getenv("KOKORO_BASE_URL", "http://localhost:8880/v1")

    # Engine / turn handling
    AI_INTERVIEW_HINTS_LIMIT: int = int(os.getenv("AI_INTERVIEW_HINTS_LIMIT", "2"))
    AI_INTERVIEW_SILENCE_NUDGES_LIMIT: int = int(os.getenv("AI_INTERVIEW_SILENCE_NUDGES_LIMIT", "3"))
    AI_INTERVIEW_TURN_LOCK_TIMEOUT: float = float(os.getenv("AI_INTERVIEW_TURN_LOCK_TIMEOUT", "30"))

    # Completion / evaluation
    AI_INTERVIEW_TRIGGER_EVALUATION: bool = os.getenv("AI_INTERVIEW_TRIGGER_EVALUATION", "true").lower() in ("1", "true", "yes")

    class Config:
        env_file = ".env"
        extra = "ignore"


ai_interview_settings = AiInterviewSettings()
