"""ai_interview — self-contained, production-hardened interview module.

Design goals (non-breaking):
  - does not modify any existing interview/voice code path
  - fail-closed intent handling (never praise on LLM failure)
  - atomic, row-locked turn processing
  - token-gated API + real cloud STT/TTS adapters
"""
from app.ai_interview.engine import AiInterviewEngine
from app.ai_interview.api.routes import router as ai_interviews_router

__all__ = ["AiInterviewEngine", "ai_interviews_router"]
