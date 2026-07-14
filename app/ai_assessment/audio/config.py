from pydantic_settings import BaseSettings
from typing import Optional
import os

class VoiceSettings(BaseSettings):
    # Whisper Settings (API Fallback/Legacy)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "")
    WHISPER_API_URL: str = "https://api.openai.com/v1/audio/transcriptions"
    WHISPER_MODEL: str = "whisper-1"

    # local faster-whisper configuration
    FASTER_WHISPER_MODEL: str = os.getenv("FASTER_WHISPER_MODEL", "small")  # tiny/base/small/medium/large-v3
    FASTER_WHISPER_DEVICE: str = os.getenv("FASTER_WHISPER_DEVICE", "cpu")  # cpu/cuda
    FASTER_WHISPER_COMPUTE_TYPE: str = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8") # int8/float32/float16

    # Kokoro Settings
    KOKORO_API_KEY: Optional[str] = os.getenv("KOKORO_API_KEY", "")
    KOKORO_BASE_URL: str = os.getenv("KOKORO_BASE_URL", "http://localhost:8880/v1")
    KOKORO_DEFAULT_VOICE: str = "af_bella"

    class Config:
        env_file = ".env"
        extra = "ignore"

voice_settings = VoiceSettings()
