import logging
from app.ai.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.gemini_prov = GeminiProvider()

    def generate_report_feedback(self, score: float, accuracy: float, class_name: str, subject_name: str = "", student_name: str = "") -> str:
        if self.gemini_prov.is_configured():
            try:
                prompt = (
                    f"Student Name: {student_name}\n"
                    f"Assigned Class: {class_name}\n"
                    f"Subject: {subject_name}\n"
                    f"Total Score: {score}%\n"
                    f"Accuracy Rate: {accuracy}%\n"
                )
                system_instruction = (
                    "You are an expert primary school academic advisor. "
                    "Generate a personalized, encouraging report feedback paragraph for this student's performance. "
                    "Identify potential areas of strength and weakness based on their score, and suggest actionable, pedagogical "
                    "steps for improvement in 2-3 sentences. Keep it warm, constructive, and suitable for primary school student/parents."
                )
                feedback = self.gemini_prov.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_mode=False,
                    model_name="gemini-2.0-flash"
                )
                return feedback.strip()
            except Exception as e:
                logger.error(f"Gemini report feedback generation failed: {e}")

        # Default fallback response
        if score >= 80:
            return f"Excellent performance in {subject_name or 'class'}! The student has demonstrated a strong understanding of concepts with {accuracy}% accuracy. Focus on maintaining these study habits."
        elif score >= 60:
            return f"Good effort in {subject_name or 'class'}. The student scored {score}%. Improving accuracy on complex questions is advised. Practice foundational concepts."
        else:
            return f"Pedagogical review recommended. The score of {score}% indicates gaps in understanding. Recommend review of chapter notes and guided exercises."

