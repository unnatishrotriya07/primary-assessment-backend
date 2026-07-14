from app.infrastructure.ai_providers.gemini import GeminiProvider
from app.infrastructure.ai_providers.openai import OpenAIProvider
from app.infrastructure.ai_providers.groq import GroqProvider

class AIProviderFactory:
    """
    Factory for producing configured AI model provider clients.
    """
    @staticmethod
    def get_provider(name: str):
        name_lower = name.lower()
        if "gemini" in name_lower:
            return GeminiProvider()
        elif "openai" in name_lower:
            return OpenAIProvider()
        elif "groq" in name_lower:
            return GroqProvider()
        else:
            raise ValueError(f"Unknown AI Provider: {name}")
