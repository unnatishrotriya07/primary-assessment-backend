import os
import hashlib
import re
from typing import List
import httpx

from .config import voice_settings
from .schemas import TTSRequest, SpeakRequest
from .exceptions import TTSException

class KokoroService:
    def __init__(self, base_url: str = voice_settings.KOKORO_BASE_URL, api_key: str = voice_settings.KOKORO_API_KEY):
        self.base_url = base_url
        self.api_key = api_key
        # Ensure the persistent local cache directory exists
        self.cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "cache", "tts"))
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, text: str, voice: str) -> str:
        """
        Computes a stable SHA-256 hash for the given parameter combo text+voice to use as a cache key.
        """
        payload_str = f"{text}{voice}"
        file_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{file_hash}.mp3")

    def get_cache_path(self, text: str, voice: str) -> str:
        """
        Public helper to retrieve the expected cache file path for a text and voice ID.
        """
        return self._get_cache_path(text, voice)

    def _chunk_text(self, text: str) -> List[str]:
        """
        Splits text by punctuation into manageable sentences/clauses for high-quality TTS synthesis.
        """
        # Split by sentences (using punctuation lookbehinds to preserve marks)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        for s in sentences:
            s_clean = s.strip()
            if s_clean:
                chunks.append(s_clean)
        return chunks

    async def _synthesize_chunk(self, text: str, voice: str, speed: float) -> bytes:
        """
        Synthesizes a single chunk. Looks up the cache first before calling the Kokoro API.
        """
        cache_path = self._get_cache_path(text, voice)
        
        # Check cache
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                return f.read()

        # Call remote API
        url = f"{self.base_url}/audio/speech"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        payload = {
            "model": "kokoro",
            "input": text,
            "voice": voice,
            "speed": speed
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    raise TTSException(f"Kokoro TTS API error: {response.text}")
                
                audio_content = response.content
                # Save to cache
                with open(cache_path, "wb") as f:
                    f.write(audio_content)
                return audio_content
                
            except Exception as e:
                if isinstance(e, TTSException):
                    raise
                raise TTSException(f"Kokoro TTS synthesis failed: {str(e)}")

    async def is_available(self) -> bool:
        """
        Verify if the local Kokoro container API is reachable on host/port.
        """
        from urllib.parse import urlparse
        import socket
        try:
            parsed = urlparse(self.base_url)
            host = parsed.hostname or "localhost"
            port = parsed.port
            if port is None:
                port = 443 if parsed.scheme == "https" else 80
            # Brief 0.5s timeout socket check
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except Exception:
            return False


    async def synthesize_speech(self, request: SpeakRequest) -> bytes:
        """
        Process long text by chunking, running cached TTS synthesis,
        and concatenating frames into a single MP3 output.
        """
        voice = request.voice or voice_settings.KOKORO_DEFAULT_VOICE
        speed = request.speed or 1.0
        
        # Check cache for full combined text first
        full_cache_path = self._get_cache_path(request.text, voice)
        if os.path.exists(full_cache_path):
            with open(full_cache_path, "rb") as f:
                return f.read()
        
        chunks = self._chunk_text(request.text)
        if not chunks:
            raise TTSException("Text input is empty or invalid.")

        combined_audio = b""
        for chunk in chunks:
            chunk_audio = await self._synthesize_chunk(chunk, voice, speed)
            combined_audio += chunk_audio
            
        # Cache full combined audio permanently for future students
        with open(full_cache_path, "wb") as f:
            f.write(combined_audio)
            
        return combined_audio

    async def synthesize(self, request: TTSRequest) -> bytes:
        """
        Compatibility wrapper for legacy interface.
        """
        speak_req = SpeakRequest(
            text=request.text,
            voice=request.voice_id,
            speed=request.speed
        )
        return await self.synthesize_speech(speak_req)

# Global singleton helper
_kokoro_service_instance = KokoroService()

def get_kokoro_service() -> KokoroService:
    return _kokoro_service_instance
