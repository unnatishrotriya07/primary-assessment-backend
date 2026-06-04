import os
import json
import logging
from app.core.config import settings
from app.ai.gemini_provider import GeminiProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

class QuestionGenerator:
    def __init__(self):
        self.groq_prov = GroqProvider()
        self.gemini_prov = GeminiProvider()
        self.openai_prov = OpenAIProvider()

    def _parse_questions(self, raw_text: str) -> list:
        try:
            data = json.loads(raw_text)
            if isinstance(data, dict) and "questions" in data:
                questions = data["questions"]
            elif isinstance(data, list):
                questions = data
            else:
                raise ValueError("Response structure is neither a list nor contains 'questions' key.")
            
            if not isinstance(questions, list):
                raise ValueError("Parsed questions is not a list.")
            return questions
        except Exception as parse_err:
            logger.error(f"Failed to parse JSON response: {parse_err}. Raw text: {raw_text}")
            raise parse_err

    def generate_questions(
        self,
        subject_name: str,
        subject_code: str,
        subject_id: int,
        chapter_id: int,
        chapter_number: str,
        chapter_title: str,
        chapter_content: str,
        difficulty: str,
        cognitive_level: str,
        count: int
    ) -> tuple:
        """
        Generates questions using the hybrid cost-optimized pipeline.
        Returns:
            tuple: (list_of_questions, provider_name)
        """
        # Load prompt template
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "generate_questions.txt")
        try:
            with open(prompt_path, "r") as f:
                template = f.read()
            prompt = template.format(
                count=count,
                subject_name=subject_name,
                chapter_number=chapter_number,
                chapter_title=chapter_title,
                chapter_content=chapter_content if chapter_content else "(No text content provided)",
                difficulty=difficulty,
                cognitive_level=cognitive_level
            )
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            prompt = f"Generate {count} questions for subject {subject_name} (ID: {subject_id}), chapter {chapter_id}, difficulty {difficulty}, cognitive level {cognitive_level}."

        system_instruction = "You are a helpful assistant that generates multiple-choice questions in JSON format. The root of the JSON response must be a JSON object with a key 'questions' containing the list of questions."

        # 1. Try Groq (llama-3.3-70b-versatile)
        if self.groq_prov.is_configured():
            try:
                raw_response = self.groq_prov.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_mode=True
                )
                questions = self._parse_questions(raw_response)
                return questions, "groq"
            except Exception as groq_err:
                logger.warning(f"Groq generation failed, falling back to Gemini: {groq_err}")

        # 2. Try Gemini (gemini-2.0-flash)
        if self.gemini_prov.is_configured():
            try:
                raw_response = self.gemini_prov.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_mode=True,
                    model_name="gemini-2.0-flash"
                )
                questions = self._parse_questions(raw_response)
                return questions, "gemini"
            except Exception as gemini_err:
                logger.warning(f"Gemini generation failed, falling back to OpenAI: {gemini_err}")
        
        # 3. Try OpenAI fallback (gpt-4o-mini)
        if self.openai_prov.is_configured():
            try:
                raw_response = self.openai_prov.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_mode=True
                )
                questions = self._parse_questions(raw_response)
                return questions, "openai"
            except Exception as openai_err:
                logger.warning(f"OpenAI generation failed, falling back to mock: {openai_err}")

        # 3. Fallback to Mock Response
        logger.info("No AI providers succeeded or configured. Falling back to mock generator.")
        return self._get_mock_questions(subject_id, count), "mock"

    def _get_mock_questions(self, subject_id: int, count: int) -> list:
        # Return mock questions depending on count
        mocks = [
            {
                "text": "What is the primary function of chlorophyll in plants?",
                "options": ["Absorb water", "Absorb sunlight", "Release oxygen", "Store glucose"],
                "correct_answer": "Absorb sunlight"
            },
            {
                "text": "Which organelle is known as the powerhouse of the cell?",
                "options": ["Nucleus", "Ribosome", "Mitochondria", "Chloroplast"],
                "correct_answer": "Mitochondria"
            },
            {
                "text": "What causes day and night on Earth?",
                "options": ["The rotation of Earth on its axis", "The revolution of Earth around the Sun", "The moon's phases", "The solar wind"],
                "correct_answer": "The rotation of Earth on its axis"
            },
            {
                "text": "Which of these is a liquid at room temperature?",
                "options": ["Iron", "Oxygen", "Water", "Wood"],
                "correct_answer": "Water"
            }
        ]
        
        # Return slice matching count
        result = []
        for i in range(count):
            result.append(mocks[i % len(mocks)])
        return result
