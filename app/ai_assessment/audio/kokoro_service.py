import os
from app.ai_assessment.audio.schemas import TTSRequest, SpeakRequest
from app.ai_assessment.audio.exceptions import TTSException

class KokoroService:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "cache", "tts"))
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cache_path(self, text: str, voice: str) -> str:
        return os.path.join(self.cache_dir, "stub.mp3")

    async def is_available(self) -> bool:
        return False

    async def synthesize_speech(self, request: SpeakRequest) -> bytes:
        raise TTSException("Local Text-to-Speech is deprecated. Use browser speech APIs instead.")

    async def synthesize(self, request: TTSRequest) -> bytes:
        raise TTSException("Local Text-to-Speech is deprecated. Use browser speech APIs instead.")

# Global singleton helper
_kokoro_service_instance = KokoroService()

def get_kokoro_service() -> KokoroService:
    return _kokoro_service_instance
