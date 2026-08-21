"""Fail-closed intent classification for the interview engine.

Design rule: this module NEVER returns a "correct/praise" verdict unless the
heuristics or the Pydantic AI intent agent positively confirmed understanding.
Any exception, empty LLM response, or parse failure maps to a SAFE intent (UNKNOWN),
which the planner treats as "did not understand → encourage and retry". This is the
inverse of the legacy LangGraph behaviour which defaulted to RESONATES_ANSWER on error.
"""
import logging
from typing import Optional

from app.ai_interview import agents

logger = logging.getLogger(__name__)

INTENTS = (
    "RESONATES_ANSWER",  # understood / on track (only from positive evidence)
    "INCORRECT_ANSWER",
    "SKIP",
    "ASK_REPEAT",
    "ASK_HINT",
    "I_DONT_KNOW",
    "CONFUSED",
    "OFF_TOPIC",
    "SILENCE",
    "UNKNOWN",  # safe default — treated as "not understood"
)

REPEAT_KEYWORDS = (
    "repeat the question", "can you say it again", "dobara bolna", "dobara bolie",
    "say it again", "please repeat", "can you repeat", "repeat please", "could you repeat",
    "what did you say",
)
SKIP_KEYWORDS = (
    "skip", "next question", "move on", "pass", "leave it", "chhod", "skip this",
    "i don't want to answer", "koi baat nahi",
)
DONT_KNOW_KEYWORDS = (
    "don't know", "do not know", "dont know", "i don't know", "no idea", "forgot",
    "pata nahi", "nahi pata", "i forgot", "don't remember", "not sure",
)
HINT_KEYWORDS = (
    "hint", "clue", "help me", "help please", "sakay", "madad", "give me a hint",
)
CONFUSED_KEYWORDS = (
    "confused", "i don't understand", "didn't understand", "samajh nahi", "kya bol rahe",
    "what do you mean",
)


class IntentResult:
    __slots__ = ("intent", "reason", "from_llm")

    def __init__(self, intent: str, reason: str, from_llm: bool = False):
        self.intent = intent
        self.reason = reason
        self.from_llm = from_llm

    def to_dict(self):
        return {"intent": self.intent, "reason": self.reason}


def _classify_heuristic(response: str) -> Optional[str]:
    r = (response or "").strip().lower()
    if not r:
        return "SILENCE"

    if any(kw in r for kw in REPEAT_KEYWORDS):
        return "ASK_REPEAT"
    if any(kw in r for kw in SKIP_KEYWORDS):
        return "SKIP"
    if any(kw in r for kw in HINT_KEYWORDS):
        return "ASK_HINT"
    if any(kw in r for kw in DONT_KNOW_KEYWORDS):
        return "I_DONT_KNOW"
    if any(kw in r for kw in CONFUSED_KEYWORDS):
        return "CONFUSED"
    return None


def classify_intent(
    response: str,
    question_text: str,
    expected_concepts: list,
    provider: str = "gemini",  # kept for interface compatibility; routing handled by agents
) -> IntentResult:
    """Heuristics first, then the Pydantic AI intent agent. Fail-closed: never RESONATES on error."""
    try:
        heuristic = _classify_heuristic(response)
        if heuristic:
            return IntentResult(heuristic, f"heuristic:{heuristic}")
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("[ai_interview] heuristic classification failed: %s", e)

    if not response or not response.strip():
        return IntentResult("SILENCE", "empty response")

    try:
        out = agents.classify(response, question_text, expected_concepts or [])
    except Exception as e:
        # FAIL-CLOSED: an unexpected agent error must never produce a "correct" verdict.
        logger.error("[ai_interview] Intent agent raised (fail-closed): %s", e, exc_info=True)
        return IntentResult("UNKNOWN", "agent exception", from_llm=True)

    if out is None:
        logger.error("[ai_interview] Intent agent failed (fail-closed)")
        return IntentResult("UNKNOWN", "agent failure", from_llm=True)

    intent = str(out.intent).upper()
    if intent not in INTENTS or intent == "UNKNOWN":
        return IntentResult("UNKNOWN", "agent returned unrecognized intent", from_llm=True)
    return IntentResult(intent, str(out.reason), from_llm=True)
