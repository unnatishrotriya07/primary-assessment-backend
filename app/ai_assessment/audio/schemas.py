from pydantic import BaseModel, Field
from typing import Optional

class TTSRequest(BaseModel):
    text: str = Field(..., description="The input text to synthesize into speech.")
    voice_id: Optional[str] = Field(None, description="Select voice model override.")
    speed: Optional[float] = Field(1.0, description="Speech rate modifier.", ge=0.5, le=2.0)

class STTResponse(BaseModel):
    text: str = Field(..., description="The resulting transcribed text.")
    confidence: Optional[float] = Field(None, description="Confidence rating of transcription.")
    language: Optional[str] = Field(None, description="Detected audio language.")
    audio_url: Optional[str] = Field(None, description="The URL of the saved audio file.")

class TranscribeResponse(BaseModel):
    transcript: str = Field(..., description="The resulting transcribed text.")
    language: str = Field(..., description="The detected audio language.")
    duration: float = Field(..., description="The duration of the audio in seconds.")
    processing_time: float = Field(..., description="The time taken to process the transcription in seconds.")
    audio_url: Optional[str] = Field(None, description="The URL of the saved audio file.")

class SpeakRequest(BaseModel):
    text: str = Field(..., description="The text to convert to speech.")
    voice: Optional[str] = Field(None, description="Kokoro voice ID override.")
    speed: Optional[float] = Field(1.0, description="Speech speed rate modifier.", ge=0.5, le=2.0)
