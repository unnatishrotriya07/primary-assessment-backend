import json
import logging
import google.generativeai as genai
from app.common.config import settings

logger = logging.getLogger(__name__)

class GeminiProvider:
    """
    Client provider for Google Gemini API.
    Attempts to generate high-quality conceptual and language questions.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_instruction: str = None, json_mode: bool = False, model_name: str = None) -> str:
        if not self.is_configured():
            raise ValueError("GEMINI_API_KEY is not configured.")

        model_name = model_name or "gemini-2.0-flash"
        logger.info(f"Sending request to Gemini API (model={model_name})")
        
        generation_config = {}
        if json_mode:
            generation_config["response_mime_type"] = "application/json"
            
        model = genai.GenerativeModel(
            model_name,
            generation_config=generation_config,
            system_instruction=system_instruction
        )
        
        response = model.generate_content(prompt)
        return response.text.strip()
