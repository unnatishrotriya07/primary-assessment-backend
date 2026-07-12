from app.voice.whisper_service import get_whisper_service
from app.voice.kokoro_service import get_kokoro_service
from app.voice.schemas import SpeakRequest

class VoiceEngine:
    def __init__(self):
        self.whisper = get_whisper_service()
        self.kokoro = get_kokoro_service()

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm", content_type: str = "audio/webm") -> str:
        """
        Converts Speech (Audio bytes) to Transcript (text).
        """
        res = await self.whisper.transcribe(audio_bytes, filename, content_type)
        return res.text

    async def speak(self, text: str, voice: str = None, speed: float = 1.0) -> bytes:
        """
        Converts text to Speech (audio bytes).
        """
        req = SpeakRequest(text=text, voice=voice, speed=speed)
        return await self.kokoro.synthesize_speech(req)
