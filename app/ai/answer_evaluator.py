import json
import logging
from app.ai.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

class AnswerEvaluator:
    def __init__(self):
        self.gemini_prov = GeminiProvider()

    def evaluate(self, question, student_answer: str) -> dict:
        # Check if question is objective (has options) or is math-based
        is_objective = False
        if question.options and len(question.options) > 0:
            is_objective = True
        
        # Check if subject name contains math
        is_math = False
        if question.subject and question.subject.name:
            if "math" in question.subject.name.lower():
                is_math = True
                
        # If it is objective or math, use rule-based evaluation
        if is_objective or is_math:
            correct_answer = question.correct_answer or ""
            is_correct = self._rule_based_evaluate(correct_answer, student_answer)
            explanation = "Correct!" if is_correct else f"Incorrect. The correct answer is '{correct_answer}'."
            return {
                "is_correct": is_correct,
                "explanation": explanation,
                "evaluator": "rule-based"
            }
            
        # Descriptive answer evaluation using Gemini
        if self.gemini_prov.is_configured():
            try:
                prompt = (
                    f"Question: {question.text}\n"
                    f"Expected Answer: {question.correct_answer}\n"
                    f"Student Answer: {student_answer}\n"
                )
                system_instruction = (
                    "You are an expert primary school teacher grading descriptive student answers. "
                    "Evaluate the student's answer against the expected answer. "
                    "Determine if the student has understood the concept correctly (even if there are spelling/grammar issues or if it is phrased differently). "
                    "You must respond with a JSON object containing keys:\n"
                    "- 'is_correct': a boolean (true or false)\n"
                    "- 'explanation': a brief (1-2 sentences) encouraging feedback detailing what was correct or where they can improve."
                )
                
                raw_response = self.gemini_prov.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_mode=True,
                    model_name="gemini-2.0-flash"
                )
                
                res = json.loads(raw_response)
                return {
                    "is_correct": bool(res.get("is_correct", False)),
                    "explanation": res.get("explanation", "Completed evaluation."),
                    "evaluator": "gemini"
                }
            except Exception as e:
                logger.error(f"Gemini evaluation failed: {e}")
                # Fallback
                is_correct = self._rule_based_evaluate(question.correct_answer or "", student_answer)
                return {
                    "is_correct": is_correct,
                    "explanation": f"Completed fallback evaluation (Gemini unavailable).",
                    "evaluator": "fallback"
                }
        else:
            is_correct = self._rule_based_evaluate(question.correct_answer or "", student_answer)
            return {
                "is_correct": is_correct,
                "explanation": f"Completed fallback evaluation (Gemini not configured).",
                "evaluator": "fallback"
            }

    def _rule_based_evaluate(self, correct: str, student: str) -> bool:
        c = correct.strip().lower()
        s = student.strip().lower()
        if c == s:
            return True
        # Try float comparison for numeric/math questions
        try:
            if float(c) == float(s):
                return True
        except ValueError:
            pass
        return False

