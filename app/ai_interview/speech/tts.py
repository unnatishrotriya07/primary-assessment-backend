"""Real cloud TTS adapters for the interview module (non-breaking, additive).

Provider selection via AI_INTERVIEW_TTS_PROVIDER (default: elevenlabs).
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.ai_interview.config import ai_interview_settings

logger = logging.getLogger(__name__)


class TTSProvider(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    async def synthesize(self, text: str, voice: Optional[str] = None, speed: float = 1.0) -> bytes:
        ...


class ElevenLabsTTSProvider(TTSProvider):
    def __init__(self, api_key: Optional[str] = None, default_voice: Optional[str] = None):
        self.api_key = api_key
        self.default_voice = default_voice or ai_interview_settings.ELEVENLABS_DEFAULT_VOICE

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def synthesize(self, text: str, voice: Optional[str] = None, speed: float = 1.0) -> bytes:
        voice_id = voice or self.default_voice
        url = f"{ai_interview_settings.ELEVENLABS_TTS_URL.rstrip('/')}/{voice_id}"
        payload = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"speed": speed}}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={"xi-api-key": self.api_key, "Accept": "audio/mpeg", "Content-Type": "application/json"},
                json=payload,
            )
        if resp.status_code != 200:
            raise RuntimeError(f"ElevenLabs TTS failed: {resp.status_code} {resp.text[:300]}")
        return resp.content


class KokoroTTSProvider(TTSProvider):
    """OpenAI-style /audio/speech endpoint served by a local Kokoro container."""

    def is_configured(self) -> bool:
        return True  # local container needs no key

    async def synthesize(self, text: str, voice: Optional[str] = None, speed: float = 1.0) -> bytes:
        url = f"{ai_interview_settings.KOKORO_BASE_URL.rstrip('/')}/audio/speech"
        payload = {"model": "kokoro", "input": text, "voice": voice or "af_bella", "speed": speed}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Kokoro TTS failed: {resp.status_code} {resp.text[:300]}")
        return resp.content


_elevenlabs: Optional[ElevenLabsTTSProvider] = None
_kokoro: Optional[KokoroTTSProvider] = None


def get_tts_provider() -> TTSProvider:
    global _elevenlabs, _kokoro
    provider = ai_interview_settings.AI_INTERVIEW_TTS_PROVIDER.lower()
    if provider == "elevenlabs":
        if _elevenlabs is None:
            import os
            _elevenlabs = ElevenLabsTTSProvider(api_key=os.getenv("ELEVENLABS_API_KEY", ""))
        return _elevenlabs
    if provider == "kokoro":
        if _kokoro is None:
            _kokoro = KokoroTTSProvider()
        return _kokoro
    raise ValueError(f"Unsupported TTS provider: {provider}")
