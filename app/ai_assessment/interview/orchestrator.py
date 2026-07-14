import random
from app.ai_assessment.interview.conversation import ConversationManager

class InterviewOrchestrator:
    """
    Implements the core dialog state machine logic.
    Decides whether the student needs hints, follow-up questions, or should proceed.
    """
    def __init__(self):
        self.conv_mgr = ConversationManager()

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
            next_speech = self.conv_mgr.rewrite_with_persona("What did you enjoy doing today?", persona)

        elif current_state == "comfort_conv":
            if comfort_idx == 1:
                new_comfort_idx = 2
                next_speech = self.conv_mgr.rewrite_with_persona("Ready to learn together?", persona)
            else:
                next_state = "interview"
                new_current_idx = 0
                first_q = questions[0] if len(questions) > 0 else {"q": "Let's begin!"}
                q_text = first_q.get("text") or first_q.get("q") or "Let's begin!"
                next_speech = self.conv_mgr.rewrite_with_persona(f"Great! Let's start with this. {q_text}", persona)

        elif current_state in ["interview", "HINT", "FOLLOWUP"]:
            q = questions[current_idx] if current_idx < len(questions) else None
            if q:
                analysis = self.conv_mgr.analyze_response_realtime(q, student_response)
                is_struggling = analysis.get("struggle", False) or self.conv_mgr.check_heuristic_struggle(student_response)
                coverage = analysis.get("concept_coverage", 0.0)

                q_hints = q.get("hints") or []
                q_followups = q.get("followups") or []
                min_coverage = q.get("minimum_coverage", 0.6)

                if is_struggling and hints_used < len(q_hints):
                    next_state = "HINT"
                    active_hint = q_hints[hints_used]
                    next_speech = self.conv_mgr.rewrite_with_persona(active_hint, persona)
                    new_hints_used = hints_used + 1
                elif coverage < min_coverage and followups_used < len(q_followups):
                    next_state = "FOLLOWUP"
                    followup_q = q_followups[followups_used]
                    next_speech = self.conv_mgr.rewrite_with_persona(followup_q, persona)
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
                        next_speech = self.conv_mgr.rewrite_with_persona(
                            f"{encouragement} Let's try this next one. {next_q_text}", 
                            persona
                        )
                    else:
                        next_state = "GOODBYE"
                        next_speech = self.conv_mgr.rewrite_with_persona(
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
