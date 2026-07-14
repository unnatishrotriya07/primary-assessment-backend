import os
import json
import logging
from app.core.config import settings
from app.ai.gemini_provider import GeminiProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.groq_provider import GroqProvider
from app.ai_assessment.prompts import loader

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
        count: int,
        question_type: str = "mixed",
        selected_text: str = None
    ) -> tuple:
        """
        Generates questions using the hybrid cost-optimized pipeline.
        Returns:
            tuple: (list_of_questions, provider_name)
        """
        try:
            prompt = loader.load_generate_questions(
                count=count,
                subject_name=subject_name,
                chapter_number=chapter_number,
                chapter_title=chapter_title,
                chapter_content=chapter_content if chapter_content else "(No text content provided)",
                difficulty=difficulty,
                cognitive_level=cognitive_level,
                selected_text=selected_text if selected_text else ""
            )
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            prompt = f"Generate {count} questions for subject {subject_name} (ID: {subject_id}), chapter {chapter_id}, difficulty {difficulty}, cognitive level {cognitive_level}."

        system_instruction = "You are a helpful assistant that generates educational questions in JSON format. The root of the JSON response must be a JSON object with a key 'questions' containing the list of questions."

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
        return self._get_mock_questions(subject_id, count, question_type), "mock"

    def _get_mock_questions(self, subject_id: int, count: int, question_type: str = "mixed") -> list:
        # Return mock questions depending on type and count
        mcqs = [
            {
                "text": "What is the primary function of chlorophyll in plants?",
                "options": ["Absorb water", "Absorb sunlight", "Release oxygen", "Store glucose"],
                "correct_answer": "Absorb sunlight",
                "question_type": "mcq",
                "source": "NCERT Textbook",
                "section": "Introduction",
                "page": "Page 1",
                "confidence": 98,
                "reference_text": "Chlorophyll pigments absorb sunlight to perform photosynthesis."
            },
            {
                "text": "Which organelle is known as the powerhouse of the cell?",
                "options": ["Nucleus", "Ribosome", "Mitochondria", "Chloroplast"],
                "correct_answer": "Mitochondria",
                "question_type": "mcq",
                "source": "NCERT Textbook",
                "section": "Introduction",
                "page": "Page 2",
                "confidence": 99,
                "reference_text": "Mitochondria release energy in the form of ATP from cells."
            },
            {
                "text": "What causes day and night on Earth?",
                "options": ["The rotation of Earth on its axis", "The revolution of Earth around the Sun", "The moon's phases", "The solar wind"],
                "correct_answer": "The rotation of Earth on its axis",
                "question_type": "mcq",
                "source": "NCERT Textbook",
                "section": "Let us Play",
                "page": "Page 5",
                "confidence": 95,
                "reference_text": "The Earth rotates around its axis once every 24 hours causing day and night."
            },
            {
                "text": "Which of these is a liquid at room temperature?",
                "options": ["Iron", "Oxygen", "Water", "Wood"],
                "correct_answer": "Water",
                "question_type": "mcq",
                "source": "NCERT Textbook",
                "section": "Exercises",
                "page": "Page 8",
                "confidence": 96,
                "reference_text": "Water is a liquid at room temperature."
            }
        ]
        titas = [
            {
                "text": "Explain why leaves appear green in color.",
                "options": [],
                "correct_answer": "Leaves appear green because chlorophyll pigments absorb red and blue light waves and reflect green light.",
                "question_type": "tita",
                "source": "NCERT Textbook",
                "section": "Introduction",
                "page": "Page 1",
                "confidence": 98,
                "reference_text": "Chlorophyll reflects green light, making the leaf look green."
            },
            {
                "text": "Describe the main role of the mitochondria in a cell.",
                "options": [],
                "correct_answer": "The mitochondria produce ATP (energy) through cellular respiration to power cell functions.",
                "question_type": "tita",
                "source": "NCERT Textbook",
                "section": "Introduction",
                "page": "Page 2",
                "confidence": 99,
                "reference_text": "The mitochondria produce energy for the cell."
            },
            {
                "text": "What is the cause of day and night on Earth?",
                "options": [],
                "correct_answer": "Day and night is caused by the Earth rotating on its axis, which exposes different halves to the sun.",
                "question_type": "tita",
                "source": "NCERT Textbook",
                "section": "Let us Play",
                "page": "Page 5",
                "confidence": 95,
                "reference_text": "The Earth rotates on its axis."
            },
            {
                "text": "Identify which common substance is a liquid at room temperature.",
                "options": [],
                "correct_answer": "Water is a liquid at room temperature.",
                "question_type": "tita",
                "source": "NCERT Textbook",
                "section": "Exercises",
                "page": "Page 8",
                "confidence": 96,
                "reference_text": "Water is a liquid."
            }
        ]
        
        if question_type == "mcq":
            candidates = mcqs
        elif question_type == "tita":
            candidates = titas
        else:
            candidates = []
            for i in range(max(len(mcqs), len(titas))):
                if i < len(mcqs):
                    candidates.append(mcqs[i])
                if i < len(titas):
                    candidates.append(titas[i])

        # Return slice matching count
        result = []
        for i in range(count):
            result.append(candidates[i % len(candidates)])
        return result
