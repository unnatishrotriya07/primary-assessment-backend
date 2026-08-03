import logging
from typing import Dict, Any, List, Optional
from app.ai_assessment.interview.ai_orchestrator import AIOrchestrator

logger = logging.getLogger(__name__)

CONVERSATION_SYSTEM_INSTRUCTION = """You are Buddy, a friendly, patient, and encouraging virtual school teacher conducting a learning assessment conversation with a student.

YOUR PERSONALITY AND TONE:
- Be warm, encouraging, supportive, and kind.
- Act like a patient, human teacher, not a robotic AI.
- Adjust your vocabulary complexity and response length strictly based on the student's grade:
  * Grade 1-2: Cheerful, very simple words, warm/expressive tone. Keep your response extremely short (maximum 8 words).
  * Grade 3-5: Simple, encouraging teacher-like tone. Keep response short (maximum 15 words).
  * Grade 6-8: Friendly, structured tone. Keep response natural (maximum 20 words).
  * Grade 9-10: Calm, supportive, formal examiner tone. Keep response professional (maximum 25 words).

CRITICAL RULES:
- Never say "Wrong", "Incorrect", "No", or use any negative/judgmental words.
- Never reveal correct answers, solutions, or options.
- Never mention score, marks, grading, test, exam, LLM, AI, prompt, or model.
- If a hint is requested or the student struggles, give a short clue that guides their thinking, but NEVER reveal the complete answer.
- Always be concise, clear, and direct.
"""

class ConversationManager:
    def __init__(self):
        self.orchestrator = AIOrchestrator()

    def _get_recent_history(self, history: List[Dict[str, str]], limit: int = 3) -> str:
        """
        Extract only the last few turns of context to avoid sending the complete transcript.
        """
        if not history:
            return ""
        recent = history[-limit:]
        lines = []
        for turn in recent:
            role = "Buddy (Teacher)" if turn.get("role") == "ai" else "Student"
            lines.append(f"{role}: {turn.get('text', '')}")
        return "\n".join(lines)

    def generate_welcome_speech(
        self,
        student_name: str,
        student_grade: str,
        comfort_index: int,
        student_response: str,
        current_question: str,
        history: List[Dict[str, str]] = None
    ) -> str:
        """
        Generates natural welcome/comfort building speeches using LLM.
        """
        recent_context = self._get_recent_history(history or [])
        
        if comfort_index == 0:
            prompt = f"Welcome the student named {student_name} to the learning session. Ask them how they are doing today."
        else:
            prompt = f"The student named {student_name} said they are doing: '{student_response}' in response to 'how are you'. Acknowledge their response warmly, and then say that we are going to start the assessment now in a friendly, encouraging way."

        user_prompt = ""
        if recent_context:
            user_prompt += f"Recent Dialogue Context:\n{recent_context}\n\n"
        user_prompt += f"Student Grade: {student_grade}\nInstruction: {prompt}"
        
        try:
            logger.info(f"[ConversationManager] Generating welcome speech for comfort_index={comfort_index}")
            speech = self.orchestrator.generate(
                prompt=user_prompt,
                system_instruction=CONVERSATION_SYSTEM_INSTRUCTION,
                preferred_provider="gemini"
            )
            return speech
        except Exception as e:
            logger.error(f"Error generating welcome speech: {e}", exc_info=True)
            # Fallback
            if comfort_index == 0:
                return f"Hello {student_name}! I am Buddy. How are you today?"
            else:
                return "That's wonderful! Let's start with our first question."

    def generate_assessment_speech(
        self,
        student_name: str,
        student_grade: str,
        action: str,
        current_question: str,
        student_response: str,
        active_hint: Optional[str] = None,
        next_question: Optional[str] = None,
        history: List[Dict[str, str]] = None
    ) -> str:
        """
        Generates natural teacher responses for assessment turns using LLM.
        """
        recent_context = self._get_recent_history(history or [])

        if action == "repeat":
            prompt = f"The student requested to repeat the question. Say something friendly to introduce that you are repeating the question now."
        elif action == "hint":
            prompt = f"The student is struggling or requested a hint. Provide a short, helpful clue for the question: '{current_question}'. Use this concept to guide your hint: '{active_hint or 'think step by step'}'. Do not give away the answer."
        elif action == "encourage_retry":
            prompt = f"The student remained silent or hesitated. Greet them with warm encouragement, telling them to take their time and say whatever they think."
        elif action == "encourage_topic":
            prompt = f"The student went off-topic. Acknowledge what they said: '{student_response}' briefly and friendly, then redirect them to focus back on the question: '{current_question}'."
        elif action == "skip":
            prompt = f"The student struggled or wanted to move on from the question: '{current_question}'. Generate a very brief, warm reassuring phrase (maximum 3 words, e.g. 'No problem!', 'All good!', or 'Let's keep going!'). Do not add any other words or questions."
        else: # praise / transition
            prompt = f"The student answered the question: '{current_question}' with: '{student_response}'. Generate a very brief, warm praise (maximum 3 words, e.g. 'Great job!', 'Well done!', or 'Nice thinking!'). Do not add any other words or questions."

        user_prompt = ""
        if recent_context:
            user_prompt += f"Recent Dialogue Context:\n{recent_context}\n\n"
        user_prompt += f"Student Name: {student_name}\nStudent Grade: {student_grade}\nInstruction: {prompt}"

        try:
            logger.info(f"[ConversationManager] Generating assessment speech for action={action}")
            speech = self.orchestrator.generate(
                prompt=user_prompt,
                system_instruction=CONVERSATION_SYSTEM_INSTRUCTION,
                preferred_provider="gemini"
            )
            speech = speech.strip()
            if action in ["skip", "praise"] and next_question:
                if speech and not speech.endswith(('.', '!', '?')):
                    speech += "!"
                speech = f"{speech} {next_question}"
            return speech
        except Exception as e:
            logger.error(f"Error generating assessment speech: {e}", exc_info=True)
            # Fallback
            if action == "repeat":
                return "Sure, let me repeat it."
            elif action == "hint":
                return f"Here is a small clue: {active_hint or 'Try breaking it down.'}"
            elif action == "encourage_retry":
                return "Take your time! Tell me whatever you remember."
            elif action == "encourage_topic":
                return f"That's interesting! Let's focus back on the question: {current_question}"
            
            speech = "No problem at all!" if action == "skip" else "Great effort!"
            if next_question:
                speech = f"{speech} {next_question}"
            return speech

    def generate_goodbye_speech(self, student_name: str, student_grade: str, history: List[Dict[str, str]] = None) -> str:
        """
        Generates a friendly wrap-up message.
        """
        recent_context = self._get_recent_history(history or [])
        prompt = f"The assessment is complete. Thank the student named {student_name} warmly, praise their effort, and say goodbye."
        
        user_prompt = ""
        if recent_context:
            user_prompt += f"Recent Dialogue Context:\n{recent_context}\n\n"
        user_prompt += f"Student Name: {student_name}\nStudent Grade: {student_grade}\nInstruction: {prompt}"

        try:
            logger.info("[ConversationManager] Generating goodbye speech")
            speech = self.orchestrator.generate(
                prompt=user_prompt,
                system_instruction=CONVERSATION_SYSTEM_INSTRUCTION,
                preferred_provider="gemini"
            )
            return speech
        except Exception as e:
            logger.error(f"Error generating goodbye speech: {e}", exc_info=True)
            return f"Thank you so much {student_name}! We have finished all our questions today. You did wonderful! Goodbye!"
