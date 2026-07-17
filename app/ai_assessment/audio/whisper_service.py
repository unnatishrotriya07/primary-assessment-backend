import time
from typing import Optional
from app.ai_assessment.audio.schemas import STTResponse, TranscribeResponse
from app.ai_assessment.audio.exceptions import STTException

class WhisperService:
    def __init__(self):
        self._local_model = None

    async def transcribe_local(self, audio_bytes: bytes) -> TranscribeResponse:
        raise STTException("Local Speech-to-Text is deprecated. Use browser speech APIs instead.")

    async def transcribe(self, audio_bytes: bytes, filename: str, content_type: str = "audio/webm") -> STTResponse:
        raise STTException("Local Speech-to-Text is deprecated. Use browser speech APIs instead.")

    def is_available(self) -> bool:
        return False

# Global singleton helper
_whisper_service_instance = WhisperService()

def get_whisper_service() -> WhisperService:
    return _whisper_service_instance
