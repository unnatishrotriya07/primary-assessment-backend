from fastapi import HTTPException, status

class VoiceException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)

class STTException(VoiceException):
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_502_BAD_GATEWAY)

class TTSException(VoiceException):
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_502_BAD_GATEWAY)

class AudioFormatException(VoiceException):
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)
