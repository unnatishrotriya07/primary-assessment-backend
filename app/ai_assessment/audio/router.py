from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
import os
from typing import Optional

from app.ai_assessment.audio.schemas import STTResponse, TTSRequest, TranscribeResponse, SpeakRequest
from app.ai_assessment.audio.whisper_service import WhisperService, get_whisper_service
from app.ai_assessment.audio.kokoro_service import KokoroService, get_kokoro_service
from app.ai_assessment.audio.audio_utils import validate_audio_file

router = APIRouter()

def save_uploaded_audio(content: bytes, interview_id: int, question_index: int) -> str:
    folder = os.path.join("static", "interviews", str(interview_id))
    os.makedirs(folder, exist_ok=True)
    
    filename = f"q{question_index + 1}.wav"
    filepath = os.path.join(folder, filename)
    
    with open(filepath, "wb") as f:
        f.write(content)
        
    return f"/static/interviews/{interview_id}/{filename}"

@router.get("/health")
async def health_check(
    whisper_service: WhisperService = Depends(get_whisper_service),
    kokoro_service: KokoroService = Depends(get_kokoro_service)
):
    whisper_ok = whisper_service.is_available()
    kokoro_ok = await kokoro_service.is_available()
    
    status_str = "ok" if (whisper_ok and kokoro_ok) else "degraded"
    
    return {
        "status": status_str,
        "whisper": "available" if whisper_ok else "unavailable",
        "kokoro": "available" if kokoro_ok else "unavailable"
    }

@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    interview_id: Optional[int] = Form(None),
    question_index: Optional[int] = Form(None),
    whisper_service: WhisperService = Depends(get_whisper_service)
):
    validate_audio_file(file.filename, file.content_type)
    content = await file.read()
    res = await whisper_service.transcribe(content, file.filename, file.content_type)
    
    audio_url = None
    if interview_id is not None and question_index is not None:
        audio_url = save_uploaded_audio(content, interview_id, question_index)
        
    return STTResponse(
        text=res.text,
        language=res.language,
        confidence=res.confidence,
        audio_url=audio_url
    )

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    interview_id: Optional[int] = Form(None),
    question_index: Optional[int] = Form(None),
    whisper_service: WhisperService = Depends(get_whisper_service)
):
    validate_audio_file(file.filename, file.content_type)
    content = await file.read()
    res = await whisper_service.transcribe_local(content)
    
    audio_url = None
    if interview_id is not None and question_index is not None:
        audio_url = save_uploaded_audio(content, interview_id, question_index)
        
    return TranscribeResponse(
        transcript=res.transcript,
        language=res.language,
        duration=res.duration,
        processing_time=res.processing_time,
        audio_url=audio_url
    )

@router.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    kokoro_service: KokoroService = Depends(get_kokoro_service)
):
    voice_id = request.voice_id or "af_bella"
    cache_path = kokoro_service.get_cache_path(request.text, voice_id)
    if not os.path.exists(cache_path):
        await kokoro_service.synthesize(request)
    return FileResponse(cache_path, media_type="audio/mpeg")

@router.post("/speak")
async def speak_text(
    request: SpeakRequest,
    kokoro_service: KokoroService = Depends(get_kokoro_service)
):
    voice = request.voice or "af_bella"
    cache_path = kokoro_service.get_cache_path(request.text, voice)
    if not os.path.exists(cache_path):
        await kokoro_service.synthesize_speech(request)
    return FileResponse(cache_path, media_type="audio/mpeg")
