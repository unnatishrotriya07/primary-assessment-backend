from app.ai_assessment.interview.orchestrator import InterviewOrchestrator

class InterviewEngine:
    """
    Delegate/redirect to refactored InterviewOrchestrator.
    """
    def __init__(self):
        self.orchestrator = InterviewOrchestrator()

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
        return self.orchestrator.process_interview_flow(
            questions,
            current_idx,
            current_state,
            comfort_idx,
            hints_used,
            followups_used,
            student_response,
            persona,
            student_name
        )
