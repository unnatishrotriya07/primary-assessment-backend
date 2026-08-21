"""Intent → action planning. Guarantees a neutral action for UNKNOWN/silence paths.

Action vocabulary: repeat, hint, encourage_retry, encourage_topic, skip, praise.
A "praise/transition" action is produced ONLY from positive intent evidence.
"""

ACTIONS = ("repeat", "hint", "encourage_retry", "encourage_topic", "skip", "praise")

# Intents that signal genuine understanding -> praise/transition.
_PRAISE_INTENTS = {"RESONATES_ANSWER"}
# Intents that are neutral and must never be praised.
_NEUTRAL_INTENTS = {
    "UNKNOWN", "SILENCE", "I_DONT_KNOW", "CONFUSED", "OFF_TOPIC", "INCORRECT_ANSWER",
}


def plan_action(
    intent: str,
    hints_used: int,
    hints_limit: int,
    silence_nudges: int,
    silence_nudges_limit: int,
) -> dict:
    """Return {'action': ..., 'advance': bool, 'reason': str}.

    `advance` indicates whether the engine should move past the current turn
    (used by praise/skip and auto-skip after repeated silence).
    """
    intent = (intent or "UNKNOWN").upper()

    if intent == "ASK_REPEAT":
        return {"action": "repeat", "advance": False, "reason": "student asked to repeat"}
    if intent == "ASK_HINT":
        if hints_used < hints_limit:
            return {"action": "hint", "advance": False, "reason": "hint requested"}
        return {"action": "encourage_retry", "advance": False, "reason": "no hints remaining"}
    if intent == "SKIP":
        return {"action": "skip", "advance": True, "reason": "student skipped"}
    if intent == "I_DONT_KNOW" or intent == "INCORRECT_ANSWER":
        if hints_used < hints_limit:
            return {"action": "hint", "advance": False, "reason": f"{intent.lower()} -> hint"}
        return {"action": "encourage_retry", "advance": False, "reason": "hints exhausted"}
    if intent == "CONFUSED" or intent == "OFF_TOPIC":
        return {"action": "encourage_topic", "advance": False, "reason": f"{intent.lower()}"}
    if intent == "SILENCE":
        if silence_nudges >= silence_nudges_limit:
            # Auto-skip is neutral (not praise): the answer is simply not graded.
            return {"action": "skip", "advance": True, "reason": "silence auto-skip"}
        return {"action": "encourage_retry", "advance": False, "reason": "silence"}
    if intent in _PRAISE_INTENTS:
        return {"action": "praise", "advance": True, "reason": "positive evidence"}

    # Fail-closed: UNKNOWN or anything unrecognized -> neutral retry, no advance.
    return {"action": "encourage_retry", "advance": False, "reason": f"unknown intent ({intent})"}
