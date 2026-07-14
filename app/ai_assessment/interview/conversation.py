import json
from app.ai.groq_provider import GroqProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai_assessment.prompts import loader

class ConversationManager:
    """
    Handles rewriting text to match student personas and analyzing realtime responses.
    """
    def __init__(self):
        self.groq_prov = GroqProvider()
        self.gemini_prov = GeminiProvider()

    def rewrite_with_persona(self, text: str, persona: dict) -> str:
        prompt = loader.load_persona_rewrite(
            persona_style=persona.get('style', 'friendly, encouraging'),
            sentence_limit=persona.get('sentence_limit', '8-15 words'),
            text=text
        )
        try:
            if self.groq_prov.is_configured():
                res = self.groq_prov.generate(prompt=prompt, max_tokens=100, temperature=0.7)
                if res and res.strip():
                    return res.strip()
            if self.gemini_prov.is_configured():
                res = self.gemini_prov.generate(prompt=prompt, max_tokens=100, temperature=0.7, model_name="gemini-2.0-flash")
                if res and res.strip():
                    return res.strip()
        except Exception:
            pass
        return text

    def analyze_response_realtime(self, question: dict, student_response: str) -> dict:
        expected = question.get("expected_concepts") or []
        q_text = question.get("text") or question.get("q") or ""
        correct_ans = question.get("correct_answer") or question.get("expected_concepts") or ""
        
        prompt = loader.load_response_analysis(
            question_text=q_text,
            correct_answer=correct_ans,
            expected_concepts=expected,
            student_response=student_response
        )
        try:
            if self.groq_prov.is_configured():
                res = self.groq_prov.generate(prompt=prompt, json_mode=True, max_tokens=50, temperature=0.0)
                return json.loads(res)
            if self.gemini_prov.is_configured():
                res = self.gemini_prov.generate(prompt=prompt, json_mode=True, max_tokens=50, temperature=0.0, model_name="gemini-2.0-flash")
                return json.loads(res)
        except Exception:
            pass
        return {"struggle": self.check_heuristic_struggle(student_response), "concept_coverage": 0.5}

    def check_heuristic_struggle(self, text: str) -> bool:
        text_lower = text.lower().strip()
        if not text_lower or text_lower in ["(silent)", "silent", "none"]:
            return True
        struggle_words = ["don't know", "dont know", "skip", "help", "no idea", "not sure", "pass", "can't say", "cant say", "forget", "forgot"]
        return any(word in text_lower for word in struggle_words)
