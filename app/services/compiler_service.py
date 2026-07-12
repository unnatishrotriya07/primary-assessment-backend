import json
import logging
from sqlalchemy.orm import Session
from app.models.assessment import Assessment
from app.models.question import Question
from app.ai.groq_provider import GroqProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

class AssessmentCompilerService:
    def __init__(self, db: Session):
        self.db = db
        self.groq_prov = GroqProvider()
        self.gemini_prov = GeminiProvider()
        self.openai_prov = OpenAIProvider()

    def compile_assessment(self, assessment_id: int, force_recompile: bool = False) -> dict:
        """
        Compiles all questions in an assessment. Enriching each question with V2 educational metadata.
        """
        assessment = self.db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        compiled_count = 0
        for q in assessment.questions:
            # Check if already compiled
            if q.learning_objective and q.rubric and not force_recompile:
                continue

            try:
                enriched = self._enrich_question_with_ai(q)
                
                # Save V2 fields to question DB
                q.learning_objective = enriched.get("learning_objective")
                q.bloom_level = enriched.get("bloom_level") or q.cognitive_level
                q.expected_concepts = enriched.get("expected_concepts")
                q.rubric = enriched.get("rubric")
                q.common_mistakes = enriched.get("common_mistakes")
                q.hints = enriched.get("hints")
                q.followups = enriched.get("followups")
                q.maximum_followups = enriched.get("maximum_followups") or 2
                q.minimum_coverage = enriched.get("minimum_coverage") or 0.6
                q.ideal_answer_length = enriched.get("ideal_answer_length") or 50
                q.estimated_duration = enriched.get("estimated_duration") or 120
                q.scoring_rules = enriched.get("scoring_rules")

                self.db.add(q)
                compiled_count += 1
            except Exception as e:
                logger.error(f"Failed to enrich question {q.id}: {e}", exc_info=True)
                # Fallback to defaults to not fail compiler entirely
                self._apply_fallback_v2_fields(q)
                self.db.add(q)

        self.db.commit()
        return {"status": "success", "assessment_id": assessment_id, "compiled_questions": compiled_count}

    def _enrich_question_with_ai(self, question: Question) -> dict:
        prompt = f"""You are an educational assessment compiler.
Given the following test question, generate rich diagnostic metadata for school children.

Question Text: {question.text}
Correct Expected Answer: {question.correct_answer}
Difficulty: {question.difficulty}
Cognitive Level / Bloom Category: {question.cognitive_level}
Options (if MCQ): {json.dumps(question.options or [])}

Generate a JSON object with the following fields:
1. "learning_objective": A clear, concise statement of what this question measures (e.g. "Identify equivalent fractions visually").
2. "bloom_level": Choose one: "remembering", "understanding", "applying", "analyzing", "evaluating", "creating".
3. "expected_concepts": A list of 2-3 short, precise concepts or key terms expected in a correct explanation (e.g. ["numerator", "parts of a whole", "equal divisions"]).
4. "rubric": Clear conceptual grading criteria (e.g., "Must identify equivalent fraction and state that multiplying top and bottom maintains ratio.").
5. "common_mistakes": A list of 2-3 common student mistakes/misconceptions for this topic.
6. "hints": A list of 2 progressive hints to assist a struggling student.
   - Hint 1 should be a gentle guidance clue.
   - Hint 2 should be a stronger scaffolding scaffold, but NEVER reveal the correct answer directly.
7. "followups": A list of 2 diagnostic follow-up questions to ask if the student's answer has low concept coverage.
8. "maximum_followups": Integer (default to 2).
9. "minimum_coverage": Float between 0.4 and 0.8 representing required conceptual overlap (default 0.6).
10. "ideal_answer_length": Integer (expected characters for a complete descriptive answer, default 50).
11. "estimated_duration": Integer (seconds to complete, default 120).
12. "scoring_rules": Text instructions for grading.

Ensure you return ONLY a raw JSON object matching the requested schema. No markdown, no backticks, no text.
"""
        system_instruction = "You are a precise educational content compiler. Return a raw JSON object matching the requested schema exactly."
        
        # Try Groq
        if self.groq_prov.is_configured():
            try:
                res = self.groq_prov.generate(prompt=prompt, system_instruction=system_instruction, json_mode=True)
                return json.loads(res)
            except Exception as e:
                logger.warning(f"Groq failed to compile question: {e}")

        # Try Gemini
        if self.gemini_prov.is_configured():
            try:
                res = self.gemini_prov.generate(prompt=prompt, system_instruction=system_instruction, json_mode=True, model_name="gemini-2.0-flash")
                return json.loads(res)
            except Exception as e:
                logger.warning(f"Gemini failed to compile question: {e}")

        # Try OpenAI
        if self.openai_prov.is_configured():
            try:
                res = self.openai_prov.generate(prompt=prompt, system_instruction=system_instruction, json_mode=True)
                return json.loads(res)
            except Exception as e:
                logger.warning(f"OpenAI failed to compile question: {e}")

        # If all else fails, return a simulated rich object
        return self._generate_mock_compiled_fields(question)

    def _apply_fallback_v2_fields(self, q: Question):
        mock_fields = self._generate_mock_compiled_fields(q)
        q.learning_objective = mock_fields["learning_objective"]
        q.bloom_level = mock_fields["bloom_level"]
        q.expected_concepts = mock_fields["expected_concepts"]
        q.rubric = mock_fields["rubric"]
        q.common_mistakes = mock_fields["common_mistakes"]
        q.hints = mock_fields["hints"]
        q.followups = mock_fields["followups"]
        q.maximum_followups = mock_fields["maximum_followups"]
        q.minimum_coverage = mock_fields["minimum_coverage"]
        q.ideal_answer_length = mock_fields["ideal_answer_length"]
        q.estimated_duration = mock_fields["estimated_duration"]
        q.scoring_rules = mock_fields["scoring_rules"]

    def _generate_mock_compiled_fields(self, question: Question) -> dict:
        text_lower = question.text.lower()
        if "numerator" in text_lower or "denominator" in text_lower or "fraction" in text_lower:
            return {
                "learning_objective": "Understand and apply numerator/denominator concepts in fractions",
                "bloom_level": "understanding",
                "expected_concepts": ["numerator", "denominator", "division of parts"],
                "rubric": "Correctly identify numerator/denominator definitions and division parts.",
                "common_mistakes": ["inverting numerator and denominator", "confusing division with addition"],
                "hints": [
                    "Remember that the denominator is the number at the bottom showing total equal parts.",
                    "The numerator is at the top, showing the selected parts of the whole."
                ],
                "followups": [
                    "Can you tell me what the denominator represents in a fraction?",
                    "If we have a pizza, which number shows the total slices we cut?"
                ],
                "maximum_followups": 2,
                "minimum_coverage": 0.6,
                "ideal_answer_length": 60,
                "estimated_duration": 120,
                "scoring_rules": "Score based on mentioning numerator is top, denominator is bottom."
            }
        else:
            return {
                "learning_objective": "Apply general academic logic and reasoning",
                "bloom_level": question.cognitive_level or "applying",
                "expected_concepts": ["concept", "logic", "explanation"],
                "rubric": "Student provides clear semantic explanation matching correct answer.",
                "common_mistakes": ["incomplete explanation", "lack of detail"],
                "hints": [
                    "Think about how you would explain this to a classmate.",
                    "Try to break down the correct answer into simple parts."
                ],
                "followups": [
                    "Can you explain your reasoning a bit more?",
                    "What makes you think that is the right answer?"
                ],
                "maximum_followups": 2,
                "minimum_coverage": 0.6,
                "ideal_answer_length": 50,
                "estimated_duration": 120,
                "scoring_rules": "Score based on content overlap."
            }
