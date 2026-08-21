"""Pydantic AI agents for the ai_interview module (LangGraph-free).

Two typed agents replace the hand-rolled JSON parsing / provider fallback code:

  - IntentAgent  -> validated, structured intent (fail-closed via output validation)
  - BuddyAgent   -> validated Buddy speech (persona + grade-aware prompts)

Model routing is provider-agnostic via the OpenAI-compatible protocol:
  - GROQ  -> GROQ_API_KEY + GROQ_BASE_URL            (default)
  - GEMINI -> GEMINI_API_KEY + Gemini's OpenAI endpoint

Every LLM call is wrapped fail-closed: any error/validation failure falls back to a
safe static response and NEVER produces a "correct/praise" verdict from a broken path.
"""
import json
import logging
import os
from typing import Literal, Optional, List, Dict

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.ai_interview.config import ai_interview_settings

logger = logging.getLogger(__name__)

# ── Types ─────────────────────────────────────────────────────────────────────
INTENT_CATEGORIES = (
    "RESONATES_ANSWER",
    "INCORRECT_ANSWER",
    "SKIP",
    "ASK_REPEAT",
    "ASK_HINT",
    "I_DONT_KNOW",
    "CONFUSED",
    "OFF_TOPIC",
    "SILENCE",
)


class IntentOutput(BaseModel):
    intent: Literal[
        "RESONATES_ANSWER", "INCORRECT_ANSWER", "SKIP", "ASK_REPEAT",
        "ASK_HINT", "I_DONT_KNOW", "CONFUSED", "OFF_TOPIC", "SILENCE",
    ]
    reason: str = Field(description="Brief justification for the category.")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Classification confidence.")


class BuddyOutput(BaseModel):
    speech: str = Field(min_length=1, max_length=800, description="Buddy's spoken reply, in the student's language.")


BUDDY_SYSTEM_INSTRUCTION = """You are Buddy, a friendly, patient, and encouraging virtual school teacher conducting a learning assessment conversation with a student.

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
- Output only the text Buddy should speak. Never explain your reasoning.
"""

INTENT_SYSTEM_INSTRUCTION = """You are classifying a primary-school student's spoken answer to determine intent.
Categories: RESONATES_ANSWER, INCORRECT_ANSWER, SKIP, ASK_REPEAT, ASK_HINT, I_DONT_KNOW, CONFUSED, OFF_TOPIC, SILENCE.
RESONATES_ANSWER only when the student clearly attempts the question AND shows partial or full understanding of the key concept.
Be conservative: if unsure, choose CONFUSED or OFF_TOPIC, never RESONATES_ANSWER. Allow transcription artifacts."""


# ── Model factory ─────────────────────────────────────────────────────────────
def build_model() -> OpenAIChatModel:
    provider = ai_interview_settings.AI_INTERVIEW_MODEL_PROVIDER.lower()
    if provider == "gemini":
        return OpenAIChatModel(
            ai_interview_settings.AI_INTERVIEW_GEMINI_MODEL,
            provider=OpenAIProvider(
                base_url=ai_interview_settings.GEMINI_OPENAI_BASE_URL,
                api_key=os.getenv("GEMINI_API_KEY", ""),
            ),
        )
    # default: groq (OpenAI-compatible)
    return OpenAIChatModel(
        ai_interview_settings.AI_INTERVIEW_GROQ_MODEL,
        provider=OpenAIProvider(
            base_url=ai_interview_settings.GROQ_BASE_URL,
            api_key=os.getenv("GROQ_API_KEY", ""),
        ),
    )


_intent_agent: Optional[Agent] = None
_buddy_agent: Optional[Agent] = None


def intent_agent() -> Agent:
    global _intent_agent
    if _intent_agent is None:
        _intent_agent = Agent(
            build_model(),
            output_type=IntentOutput,
            instructions=INTENT_SYSTEM_INSTRUCTION,
            retries=1,
            name="intent-agent",
        )
    return _intent_agent


def buddy_agent() -> Agent:
    global _buddy_agent
    if _buddy_agent is None:
        _buddy_agent = Agent(
            build_model(),
            output_type=BuddyOutput,
            system_prompt=BUDDY_SYSTEM_INSTRUCTION,
            retries=1,
            name="buddy-agent",
        )
    return _buddy_agent


# ── Intent classification (fail-closed) ───────────────────────────────────────
def classify(response: str, question_text: str, expected_concepts: List[str]) -> Optional[IntentOutput]:
    """Run the intent agent; returns None on any failure (never guesses 'correct')."""
    if not (response or "").strip():
        return None
    prompt = (
        f"Question: {question_text}\n"
        f"Expected key concepts: {json.dumps(expected_concepts or [], ensure_ascii=False)}\n"
        f"Student response: {response}\n"
        "Classify the student's intent."
    )
    try:
        result = intent_agent().run_sync(prompt)
        return result.output
    except Exception as e:
        logger.error("[ai_interview] Intent agent failed (fail-closed): %s", e, exc_info=True)
        return None


# ── Buddy speech generation (fail-closed) ─────────────────────────────────────
def _run_buddy(prompt: str) -> Optional[str]:
    try:
        result = buddy_agent().run_sync(prompt)
        return result.output.speech.strip()
    except Exception as e:
        logger.error("[ai_interview] Buddy agent failed (fallback speech): %s", e, exc_info=True)
        return None


def _append_next(speech: str, next_question: Optional[str]) -> str:
    if speech and next_question:
        if not speech.endswith((".", "!", "?")):
            speech += "!"
        speech = f"{speech} {next_question}"
    return speech


def build_welcome_speech(
    comfort_index: int,
    student_name: str,
    student_grade: str,
    student_response: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    if comfort_index == 0:
        prompt = f"Welcome the student named {student_name} to the learning session and ask how they are doing today."
    else:
        prompt = (
            f"The student {student_name} said '{student_response}' in response to 'how are you'. "
            "Acknowledge their response warmly, then say we are going to start the assessment now, in a friendly, encouraging way."
        )
    speech = _run_buddy(prompt)
    if speech:
        return speech
    return f"Hello {student_name}! I am Buddy. How are you today?" if comfort_index == 0 else "That's wonderful! Let's start with our first question."


def build_assessment_speech(
    action: str,
    student_name: str,
    student_grade: str,
    current_question: str,
    student_response: str,
    active_hint: Optional[str] = None,
    next_question: Optional[str] = None,
) -> str:
    if action == "repeat":
        prompt = "The student asked to repeat the question. Say something friendly to introduce that you are repeating the question now."
    elif action == "hint":
        prompt = (
            f"The student is struggling or requested a hint. Provide a short, helpful clue for the question: '{current_question}'. "
            f"Use this concept to guide your hint: '{active_hint or 'think step by step'}'. Do not give away the answer."
        )
    elif action == "encourage_retry":
        prompt = "The student remained silent or hesitated. Greet them with warm encouragement, telling them to take their time and say whatever they think."
    elif action == "encourage_topic":
        prompt = (
            f"The student went off-topic. Acknowledge what they said: '{student_response}' briefly and friendly, "
            f"then redirect them to focus back on the question: '{current_question}'."
        )
    elif action == "skip":
        prompt = (
            f"The student struggled or wanted to move on from the question: '{current_question}'. "
            "Generate a very brief, warm reassuring phrase (maximum 3 words, e.g. 'No problem!', 'All good!', or 'Let's keep going!'). Do not add any other words or questions."
        )
    elif action == "praise":
        prompt = (
            f"The student answered the question: '{current_question}' with: '{student_response}'. "
            "Generate a very brief, warm praise (maximum 3 words, e.g. 'Great job!', 'Well done!', or 'Nice thinking!'). Do not add any other words or questions."
        )
    else:
        prompt = "Respond in a warm, encouraging way that invites the student to try again."

    speech = _run_buddy(prompt)
    if not speech:
        fallbacks = {
            "repeat": "Sure, let me repeat it.",
            "hint": f"Here is a small clue: {active_hint or 'Try breaking it down.'}",
            "encourage_retry": "Take your time! Tell me whatever you remember.",
            "encourage_topic": f"That's interesting! Let's focus back on the question: {current_question}",
            "skip": "No problem at all!",
            "praise": "Great effort!",
        }
        speech = fallbacks.get(action, "Take your time! Tell me whatever you remember.")

    if action in ("skip", "praise") and next_question:
        return _append_next(speech, next_question)
    return speech


def build_goodbye_speech(
    student_name: str,
    student_grade: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    prompt = f"The assessment is complete. Thank the student named {student_name} warmly, praise their effort, and say goodbye."
    speech = _run_buddy(prompt)
    if speech:
        return speech
    return f"Thank you so much {student_name}! We have finished all our questions today. You did wonderful! Goodbye!"
