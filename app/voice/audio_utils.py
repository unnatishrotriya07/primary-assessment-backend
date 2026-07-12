from typing import Tuple
from .exceptions import AudioFormatException

def validate_audio_file(filename: str, content_type: str) -> Tuple[bool, str]:
    """
    Validates standard primary-school client audio codecs.
    Ensures file types conform to wav, mp3, m4a, webm, ogg.
    """
    allowed_extensions = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".aac"}
    allowed_content_types = {
        "audio/wav", "audio/x-wav",
        "audio/mpeg", "audio/mp3",
        "audio/mp4", "audio/m4a",
        "audio/webm",
        "audio/ogg",
        "audio/aac",
        "application/octet-stream"  # Browser Blob default
    }
    
    import os
    _, ext = os.path.splitext(filename.lower())
    if ext not in allowed_extensions and content_type not in allowed_content_types:
        raise AudioFormatException(f"Unsupported audio format: extension '{ext}', Content-Type '{content_type}'")
    
    return True, ext
