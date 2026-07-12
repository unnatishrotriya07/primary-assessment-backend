import json
import random
from typing import Optional
from app.ai.groq_provider import GroqProvider
from app.ai.gemini_provider import GeminiProvider

class InterviewEngine:
    """
    InterviewEngine is responsible for the assessment logic and child dialog state machine.
    It decides whether the student needs hints, follow-up questions, or should proceed to the next question.
    """
    def __init__(self):
        self.groq_prov = GroqProvider()
        self.gemini_prov = GeminiProvider()

    def process_interview_flow(
        self,
        questions: list,
        current_idx: int,
        current_state: str,
        comfort_idx: int,
        hints_used: int,
        followups_used: int,
        student_response: str,
        persona: dict,
        student_name: str
    ) -> dict:
        """
        Input: State of the interview, student response.
        Output: Next state, next speech, next indices, hints/followups usage, active hint, and completion status.
        """
        next_speech = ""
        next_state = current_state
        active_hint = None
        new_comfort_idx = comfort_idx
        new_current_idx = current_idx
        new_hints_used = hints_used
        new_followups_used = followups_used
        is_completed = False

        if current_state == "meet_buddy":
            next_state = "comfort_conv"
            new_comfort_idx = 1
            next_speech = self._rewrite_with_persona("What did you enjoy doing today?", persona)

        elif current_state == "comfort_conv":
            if comfort_idx == 1:
                new_comfort_idx = 2
                next_speech = self._rewrite_with_persona("Ready to learn together?", persona)
            else:
                next_state = "interview"
                new_current_idx = 0
                first_q = questions[0] if len(questions) > 0 else {"q": "Let's begin!"}
                q_text = first_q.get("text") or first_q.get("q") or "Let's begin!"
                next_speech = self._rewrite_with_persona(f"Great! Let's start with this. {q_text}", persona)

        elif current_state in ["interview", "HINT", "FOLLOWUP"]:
            q = questions[current_idx] if current_idx < len(questions) else None
            if q:
                analysis = self._analyze_response_realtime(q, student_response)
                is_struggling = analysis.get("struggle", False) or self._check_heuristic_struggle(student_response)
                coverage = analysis.get("concept_coverage", 0.0)

                q_hints = q.get("hints") or []
                q_followups = q.get("followups") or []
                min_coverage = q.get("minimum_coverage", 0.6)

                if is_struggling and hints_used < len(q_hints):
                    next_state = "HINT"
                    active_hint = q_hints[hints_used]
                    next_speech = self._rewrite_with_persona(active_hint, persona)
                    new_hints_used = hints_used + 1
                elif coverage < min_coverage and followups_used < len(q_followups):
                    next_state = "FOLLOWUP"
                    followup_q = q_followups[followups_used]
                    next_speech = self._rewrite_with_persona(followup_q, persona)
                    new_followups_used = followups_used + 1
                else:
                    new_hints_used = 0
                    new_followups_used = 0
                    next_idx = current_idx + 1
                    new_current_idx = next_idx

                    if next_idx < len(questions):
                        next_state = "interview"
                        next_q = questions[next_idx]
                        next_q_text = next_q.get("text") or next_q.get("q") or ""
                        
                        encouragements = [
                            "Thoughtful answer!", "Nice thinking!", "Great effort!", 
                            "Wonderful job explaining!", "That's very clear!"
                        ]
                        encouragement = random.choice(encouragements)
                        next_speech = self._rewrite_with_persona(
                            f"{encouragement} Let's try this next one. {next_q_text}", 
                            persona
                        )
                    else:
                        next_state = "GOODBYE"
                        next_speech = self._rewrite_with_persona(
                            f"Thank you {student_name}! We have finished all questions today. You did wonderful! Goodbye!", 
                            persona
                        )
                        is_completed = True
            else:
                next_state = "GOODBYE"
                next_speech = "We are all done. Goodbye!"
                is_completed = True

        return {
            "next_state": next_state,
            "next_speech": next_speech,
            "comfort_index": new_comfort_idx,
            "current_question_index": new_current_idx,
            "hints_used_count": new_hints_used,
            "followups_used_count": new_followups_used,
            "active_hint": active_hint,
            "is_completed": is_completed
        }

    def _rewrite_with_persona(self, text: str, persona: dict) -> str:
        prompt = f"""You are a caring primary school teacher.
Rewrite the following response to match the target children grade persona:
Persona Style: {persona.get('style', 'friendly, encouraging')}
Sentence length limit: {persona.get('sentence_limit', '8-15 words')}

Response: {text}

Keep it warm and encouraging. Return ONLY the rewritten text, without quotes, prefix introduction, or markdown styling. Keep it short.
"""
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

    def _analyze_response_realtime(self, question: dict, student_response: str) -> dict:
        expected = question.get("expected_concepts") or []
        q_text = question.get("text") or question.get("q") or ""
        correct_ans = question.get("correct_answer") or question.get("expected_concepts") or ""
        
        prompt = f"""Analyze the student's answer to this question.
Question: {q_text}
Expected Answer: {correct_ans}
Expected Key Concepts: {json.dumps(expected)}
Student Answer: {student_response}

Determine:
1. Is the student struggling (silence, asking for help, "don't know", or off-topic/meaningless response)?
2. What is the semantic concept coverage (from 0.0 to 1.0) of the expected key concepts?

Return a JSON object:
{{
  "struggle": true/false,
  "concept_coverage": 0.0-1.0
}}
Return ONLY the raw JSON. No markdown, no backticks.
"""
        try:
            if self.groq_prov.is_configured():
                res = self.groq_prov.generate(prompt=prompt, json_mode=True, max_tokens=50, temperature=0.0)
                return json.loads(res)
            if self.gemini_prov.is_configured():
                res = self.gemini_prov.generate(prompt=prompt, json_mode=True, max_tokens=50, temperature=0.0, model_name="gemini-2.0-flash")
                return json.loads(res)
        except Exception:
            pass
        return {"struggle": self._check_heuristic_struggle(student_response), "concept_coverage": 0.5}

    def _check_heuristic_struggle(self, text: str) -> bool:
        text_lower = text.lower().strip()
        if not text_lower or text_lower in ["(silent)", "silent", "none"]:
            return True
        struggle_words = ["don't know", "dont know", "skip", "help", "no idea", "not sure", "pass", "can't say", "cant say", "forget", "forgot"]
        return any(word in text_lower for word in struggle_words)
