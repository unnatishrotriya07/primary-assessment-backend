import logging
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class GroqProvider:
    """
    Client provider for Groq API using OpenAI's client SDK.
    Used for fast and cheap question generation using llama-3.3-70b-versatile.
    """

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_instruction: str = None, json_mode: bool = False, model_name: str = None) -> str:
        if not self.is_configured():
            raise ValueError("GROQ_API_KEY is not configured.")

        model = model_name or "llama-3.3-70b-versatile"
        logger.info(f"Sending request to Groq API (model={model})")
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        else:
            messages.append({"role": "system", "content": "You are a helpful assistant."})
            
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {
            "model": model,
            "messages": messages,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()
