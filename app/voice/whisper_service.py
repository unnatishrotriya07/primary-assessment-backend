import io
import time
from typing import Optional
from faster_whisper import WhisperModel

from .config import voice_settings
from .schemas import STTResponse, TranscribeResponse
from .exceptions import STTException

class WhisperService:
    def __init__(self):
        # Local model instance cache
        self._local_model: Optional[WhisperModel] = None

    def _get_local_model(self) -> WhisperModel:
        """
        Lazy-loads the local faster-whisper model weights.
        Ensures model files are only loaded once.
        """
        if self._local_model is None:
            try:
                # Load the model with CPU optimization defaults
                self._local_model = WhisperModel(
                    voice_settings.FASTER_WHISPER_MODEL,
                    device=voice_settings.FASTER_WHISPER_DEVICE,
                    compute_type=voice_settings.FASTER_WHISPER_COMPUTE_TYPE
                )
            except Exception as e:
                raise STTException(f"Failed to initialize local faster-whisper model: {str(e)}")
        return self._local_model

    async def transcribe_local(self, audio_bytes: bytes) -> TranscribeResponse:
        """
        Transcribes audio locally using faster-whisper.
        Optimized for CPU execution.
        """
        start_time = time.time()
        
        if not audio_bytes:
            raise STTException("Uploaded audio file is empty.")
            
        try:
            model = self._get_local_model()
            audio_file = io.BytesIO(audio_bytes)
            
            # Run local inference
            # beam_size=5 is the default standard for quality
            segments, info = model.transcribe(audio_file, beam_size=5)
            
            # Segments is a generator. Materialize it to complete the inference.
            segments_list = list(segments)
            transcript_text = " ".join([segment.text for segment in segments_list]).strip()
            
            processing_time = round(time.time() - start_time, 3)
            
            return TranscribeResponse(
                transcript=transcript_text,
                language=info.language,
                duration=round(info.duration, 2),
                processing_time=processing_time
            )
            
        except Exception as e:
            raise STTException(f"Local transcription inference failed: {str(e)}")

    async def transcribe(self, audio_bytes: bytes, filename: str, content_type: str = "audio/webm") -> STTResponse:
        """
        Existing transcription method (for compatibility).
        Routes directly to the local service.
        """
        local_res = await self.transcribe_local(audio_bytes)
        return STTResponse(
            text=local_res.transcript,
            language=local_res.language
        )

    def is_available(self) -> bool:
        """
        Check if the Whisper model is loaded or can be successfully initialized.
        """
        if self._local_model is not None:
            return True
        try:
            self._get_local_model()
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Whisper availability check failed: {e}")
            return False

# Global singleton helper
_whisper_service_instance = WhisperService()

def get_whisper_service() -> WhisperService:
    return _whisper_service_instance

