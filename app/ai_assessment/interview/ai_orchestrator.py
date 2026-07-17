import logging
import json
from typing import Optional, Any, Dict
from app.ai.gemini_provider import GeminiProvider
from app.ai.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    AIOrchestrator decouples LLM generation from the LangGraph State Machine.
    It manages routing to preferred providers (default: Gemini) and handles fallbacks.
    """
    def __init__(self):
        self.gemini = GeminiProvider()
        self.groq = GroqProvider()

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
        preferred_provider: str = "gemini"
    ) -> str:
        providers_to_try = []
        if preferred_provider == "gemini":
            providers_to_try = [("gemini", self.gemini), ("groq", self.groq)]
        else:
            providers_to_try = [("groq", self.groq), ("gemini", self.gemini)]

        for name, provider in providers_to_try:
            try:
                if provider.is_configured():
                    logger.info(f"[AIOrchestrator] Invoking provider: {name}")
                    res = provider.generate(
                        prompt=prompt,
                        system_instruction=system_instruction,
                        json_mode=json_mode
                    )
                    if res and res.strip():
                        return res.strip()
            except Exception as e:
                logger.error(f"[AIOrchestrator] Provider {name} failed: {e}", exc_info=True)

        # Ultimate fallback
        logger.warning("[AIOrchestrator] All configured LLMs failed. Returning fallback.")
        if json_mode:
            return json.dumps({
                "intent": "ANSWER",
                "explanation": "Fallback due to LLM provider timeout/failure.",
                "confidence": 0.5
            })
        return "You are doing a wonderful job! Let's keep trying together."
