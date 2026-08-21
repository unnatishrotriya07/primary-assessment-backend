"""Real cloud STT adapters for the interview module (non-breaking, additive).

STT provider selection is driven by AI_INTERVIEW_STT_PROVIDER (default: groq).
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.ai_interview.config import ai_interview_settings

logger = logging.getLogger(__name__)


@dataclass
class STTResult:
    text: str = ""
    language: Optional[str] = None
    confidence: Optional[float] = None
    duration: Optional[float] = None
    error: Optional[str] = None


class STTProvider(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "speech.webm",
        content_type: str = "audio/webm",
        language: Optional[str] = None,
    ) -> STTResult:
        ...


class GroqSTTProvider(STTProvider):
    """OpenAI-compatible transcriptions endpoint on Groq (whisper-large-v3-turbo)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model or ai_interview_settings.GROQ_STT_MODEL
        self.base_url = (base_url or ai_interview_settings.GROQ_STT_BASE_URL).rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "speech.webm",
        content_type: str = "audio/webm",
        language: Optional[str] = None,
    ) -> STTResult:
        if not self.is_configured():
            return STTResult(error="GROQ_API_KEY is not configured.")

        url = f"{self.base_url}/audio/transcriptions"
        files = {"file": (filename, audio_bytes, content_type)}
        data = {"model": self.model}
        if language and language != "auto":
            data["language"] = language

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers={"Authorization": f"Bearer {self.api_key}"}, data=data, files=files)

        if resp.status_code != 200:
            logger.error("[ai_interview] Groq STT failed: %s %s", resp.status_code, resp.text[:300])
            return STTResult(error=f"STT provider returned {resp.status_code}")

        payload = resp.json()
        return STTResult(text=(payload.get("text") or "").strip())


# Single shared instance
_groq_stt: Optional[GroqSTTProvider] = None


def get_stt_provider() -> STTProvider:
    global _groq_stt
    provider = ai_interview_settings.AI_INTERVIEW_STT_PROVIDER.lower()
    if provider == "groq":
        if _groq_stt is None:
            import os
            _groq_stt = GroqSTTProvider(api_key=os.getenv("GROQ_API_KEY", ""))
        return _groq_stt
    raise ValueError(f"Unsupported STT provider: {provider}")
