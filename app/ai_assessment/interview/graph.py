import logging
import random
import re
import json
from typing import Dict, Any, List, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

from app.ai_assessment.interview.ai_orchestrator import AIOrchestrator

logger = logging.getLogger(__name__)

# State definition
class InterviewState(TypedDict):
    interview_id: int
    student_name: str
    student_class: str
    current_question_index: int
    session_state: str
    comfort_index: int
    questions: List[Dict[str, Any]]
    transcript: List[Dict[str, str]]
    raw_answers: List[Dict[str, Any]]
    hints_used_count: int
    followups_used_count: int
    completion_status: str
    active_hint: Optional[str]
    student_response: str
    audio_url: Optional[str]
    next_speech: str
    intent: str
    metrics: Dict[str, Any]
    action: Optional[str]  # Internal routing action
    error: Optional[str]

# Response Policy Layer
class ResponsePolicyLayer:
    """
    Ensures all AI/Buddy vocal outputs adhere strictly to educational guidelines:
    - Never say "Wrong", "Incorrect", or "No" in response to answers.
    - Never expose LLM terms like "AI", "model", "prompt", "ChatGPT", "assistant".
    - Prevent judgmental tone.
    - Inject warm support/reassurance.
    """
    @staticmethod
    def sanitize(text: str, student_name: str) -> str:
        if not text:
            return "You're doing great, let's try the next one!"

        cleaned = text.strip()
        # Remove any markdown headers, asterisks, etc.
        cleaned = re.sub(r'[\*\#\_\[\]\(\)]', '', cleaned)

        # Regex replacements to catch examiner or judgmental language
        negative_patterns = [
            (r'\b(wrong|incorrect|false|no, that is not correct|no, you are wrong)\b', "Nice try! Let's think about it together."),
            (r'\b(ai|llm|gpt|assistant|model|chatbot|machine learning|generative)\b', "Buddy"),
            (r'\b(score|grades|grading|test|examination|marks)\b', "learning journey"),
        ]

        for pattern, replacement in negative_patterns:
            cleaned = re.compile(pattern, re.IGNORECASE).sub(replacement, cleaned)

        # Basic length limiter just to be safe
        words = cleaned.split()
        if len(words) > 35:
            cleaned = " ".join(words[:30]) + "... You're doing a fantastic job, let's keep going!"

        return cleaned

# Local heuristic intent classifier
class HeuristicIntentClassifier:
    """
    Classifies standard intents like silence, repeat requests, hints, or confusion in <10ms.
    """
    @staticmethod
    def classify(text: str) -> Optional[str]:
        cleaned = text.lower().strip()
        
        # 1. Silence check
        if not cleaned or cleaned in ["(silent)", "silent", "none", "(no spoken response)"]:
            return "SILENCE"
            
        # 2. Repeat request check
        repeat_keywords = ["repeat", "say it again", "speak again", "say again", "dobara", "repeat please", "could you repeat", "what did you say"]
        if any(kw in cleaned for kw in repeat_keywords):
            return "ASK_REPEAT"
            
        # 3. I don't know / Skip check
        idk_keywords = ["don't know", "dont know", "i forgot", "forgot", "no idea", "not sure", "skip", "pass", "can't remember", "cant remember"]
        if any(kw in cleaned for kw in idk_keywords):
            return "I_DONT_KNOW"

        # 4. Ask Hint check
        hint_keywords = ["hint", "clue", "help me", "give me help", "help please"]
        if any(kw in cleaned for kw in hint_keywords):
            return "ASK_HINT"

        # 5. Confused check
        confused_keywords = ["confused", "don't understand", "dont understand", "what do you mean", "tricky"]
        if any(kw in cleaned for kw in confused_keywords):
            return "CONFUSED"

        return None

# LLM Intent classifier prompt
INTENT_SYSTEM_INSTRUCTION = """You are an educational assessment assistant.
Classify the student's verbal response into exactly one of these intents:
- ANSWER: The student provides a complete, clear, or tentative answer to the question.
- PARTIAL_ANSWER: The student provides a half-formed or partial answer, trying to explain.
- OFF_TOPIC: The student talks about something completely unrelated.
- SILENCE: Empty or meaningless sounds.

Return a raw JSON object with format:
{"intent": "ANSWER" | "PARTIAL_ANSWER" | "OFF_TOPIC" | "SILENCE"}
Do not include any formatting, backticks, or markdown."""

# LangGraph Node Implementations
def welcome_node(state: InterviewState) -> Dict[str, Any]:
    """
    Handles welcoming the child and build comfort.
    """
    logger.info("[LangGraph] Executing welcome_node")
    try:
        c_idx = state.get("comfort_index", 0)
        s_name = state.get("student_name", "friend")
        
        transcript = list(state.get("transcript") or [])
        student_resp = state.get("student_response", "")

        # Save student turn in transcript history if they responded
        if c_idx > 0 and student_resp:
            transcript.append({"role": "student", "text": student_resp, "state": "comfort_conv"})

        next_speech = ""
        next_state = "comfort_conv"
        new_c_idx = c_idx

        if c_idx == 0:
            if not student_resp or student_resp.lower() in ["", "start", "initiate_interview"]:
                next_speech = f"Hello {s_name}! I am Buddy, your learning assistant. How are you today?"
                new_c_idx = 1
            else:
                next_speech = "That's lovely! What did you enjoy doing today?"
                new_c_idx = 2
        elif c_idx == 1:
            next_speech = "That's lovely! What did you enjoy doing today?"
            new_c_idx = 2
        elif c_idx == 2:
            next_speech = "Wonderful! Are you ready to learn together?"
            new_c_idx = 3
        else:
            # Transition to first question
            next_state = "interview"
            new_c_idx = 4
            questions = state.get("questions") or []
            first_q = questions[0] if questions else {"q": "Are you ready to share your learning journey?"}
            first_q_text = first_q.get("text") or first_q.get("q") or ""
            next_speech = f"Great! Let's go to the assessment now. Here is the first question: {first_q_text}"

        # Save Buddy turn in transcript history
        transcript.append({"role": "ai", "text": next_speech, "state": next_state})

        return {
            "comfort_index": new_c_idx,
            "session_state": next_state,
            "next_speech": ResponsePolicyLayer.sanitize(next_speech, s_name),
            "transcript": transcript,
            "error": None
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in welcome_node: {e}", exc_info=True)
        return {
            "comfort_index": 3,
            "session_state": "interview",
            "next_speech": "Let's check out our first question together!",
            "error": str(e)
        }

def ask_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Presents the current academic question.
    """
    logger.info("[LangGraph] Executing ask_question_node")
    try:
        q_idx = state.get("current_question_index", 0)
        questions = state.get("questions") or []
        transcript = list(state.get("transcript") or [])

        if q_idx < len(questions):
            q = questions[q_idx]
            q_text = q.get("text") or q.get("q") or ""
            next_speech = q_text
        else:
            next_speech = "Fantastic job! We have answered all our questions."

        # Save Buddy speech in history
        transcript.append({"role": "ai", "text": next_speech, "state": "interview"})

        return {
            "next_speech": ResponsePolicyLayer.sanitize(next_speech, state.get("student_name", "")),
            "transcript": transcript,
            "session_state": "interview",
            "error": None
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in ask_question_node: {e}", exc_info=True)
        return {
            "next_speech": "Let's look at the next question.",
            "error": str(e)
        }

def listen_node(state: InterviewState) -> Dict[str, Any]:
    """
    Consumes student response and saves it in history and raw answers.
    """
    logger.info("[LangGraph] Executing listen_node")
    try:
        student_resp = state.get("student_response", "")
        q_idx = state.get("current_question_index", 0)
        questions = state.get("questions") or []
        transcript = list(state.get("transcript") or [])
        raw_answers = list(state.get("raw_answers") or [])

        # Append student message to transcript history
        transcript.append({"role": "student", "text": student_resp, "state": state.get("session_state", "interview")})

        # Append to raw answers
        if q_idx < len(questions):
            q = questions[q_idx]
            q_text = q.get("text") or q.get("q") or ""
            ans_exists = False
            for ans in raw_answers:
                if ans.get("question") == q_text:
                    ans["answer"] = ans.get("answer", "") + " | " + student_resp
                    ans_exists = True
                    break
            if not ans_exists:
                raw_answers.append({
                    "question_category": q.get("skill", "General"),
                    "question": q_text,
                    "answer": student_resp
                })

        return {
            "transcript": transcript,
            "raw_answers": raw_answers,
            "error": None
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in listen_node: {e}", exc_info=True)
        return {"error": str(e)}

def hybrid_intent_detection_node(state: InterviewState) -> Dict[str, Any]:
    """
    Detects student intent via Heuristics, falling back to Gemini Orchestration.
    """
    logger.info("[LangGraph] Executing hybrid_intent_detection_node")
    try:
        student_resp = state.get("student_response", "")
        
        # 1. Try local heuristic rules
        intent = HeuristicIntentClassifier.classify(student_resp)
        if intent:
            logger.info(f"[LangGraph] Heuristic intent classified: {intent}")
            return {"intent": intent, "error": None}

        # 2. Call AI Orchestrator
        logger.info("[LangGraph] Calling AIOrchestrator for intent classification")
        orchestrator = AIOrchestrator()
        
        q_idx = state.get("current_question_index", 0)
        questions = state.get("questions") or []
        current_q = questions[q_idx].get("text", "") if q_idx < len(questions) else ""
        
        prompt = f"Teacher's Question: {current_q}\nStudent Response: {student_resp}"
        
        raw_res = orchestrator.generate(
            prompt=prompt,
            system_instruction=INTENT_SYSTEM_INSTRUCTION,
            json_mode=True,
            preferred_provider="gemini"
        )
        
        try:
            intent = json.loads(raw_res).get("intent", "ANSWER")
        except Exception:
            intent = "ANSWER"

        logger.info(f"[LangGraph] AI intent classified: {intent}")
        return {"intent": intent, "error": None}
    except Exception as e:
        logger.error(f"[LangGraph] Error in hybrid_intent_detection_node: {e}", exc_info=True)
        return {"intent": "ANSWER", "error": str(e)}

def decision_node(state: InterviewState) -> Dict[str, Any]:
    """
    Planner node: Routes intent to planned action (repeat, hint, praise, skip).
    """
    logger.info("[LangGraph] Executing decision_node")
    try:
        intent = state.get("intent", "ANSWER")
        hints_used = state.get("hints_used_count", 0)
        q_idx = state.get("current_question_index", 0)
        questions = state.get("questions") or []
        
        q_hints = []
        if q_idx < len(questions):
            q_hints = questions[q_idx].get("hints") or []

        metrics = dict(state.get("metrics") or {})
        action = "praise"

        if intent == "ASK_REPEAT":
            action = "repeat"
        elif intent in ["I_DONT_KNOW", "CONFUSED", "ASK_HINT", "PARTIAL_ANSWER"]:
            if hints_used < len(q_hints):
                action = "hint"
            else:
                action = "skip"
        elif intent == "SILENCE":
            retries = metrics.get("retries", 0)
            if retries < 2:
                action = "encourage_retry"
            else:
                action = "skip"
        elif intent == "OFF_TOPIC":
            action = "encourage_topic"
        else:
            action = "praise"

        logger.info(f"[LangGraph] Planner decision: {action}")
        return {"action": action, "error": None}
    except Exception as e:
        logger.error(f"[LangGraph] Error in decision_node: {e}", exc_info=True)
        return {"action": "praise", "error": str(e)}

def hint_encourage_praise_node(state: InterviewState) -> Dict[str, Any]:
    """
    Executes the action decided in the Planner node.
    """
    logger.info("[LangGraph] Executing hint_encourage_praise_node")
    try:
        action = state.get("action", "praise")
        q_idx = state.get("current_question_index", 0)
        questions = state.get("questions") or []
        hints_used = state.get("hints_used_count", 0)
        transcript = list(state.get("transcript") or [])
        metrics = dict(state.get("metrics") or {})
        s_name = state.get("student_name", "")

        next_speech = ""
        active_hint = None
        new_hints_used = hints_used
        new_session_state = state.get("session_state", "interview")

        q_text = ""
        q_hints = []
        if q_idx < len(questions):
            q_text = questions[q_idx].get("text") or questions[q_idx].get("q") or ""
            q_hints = questions[q_idx].get("hints") or []

        if action == "repeat":
            next_speech = f"Sure, let me repeat it. {q_text}"
        elif action == "hint":
            active_hint = q_hints[hints_used] if hints_used < len(q_hints) else "Let's think step by step."
            new_hints_used = hints_used + 1
            next_speech = f"Here is a small clue. {active_hint}"
            new_session_state = "HINT"
        elif action == "encourage_retry":
            metrics["retries"] = metrics.get("retries", 0) + 1
            next_speech = "Take your time! Tell me whatever you remember, or what you think."
        elif action == "encourage_topic":
            next_speech = f"That sounds very interesting! But let's try to focus on our question. {q_text}"
        elif action == "skip":
            metrics["skipped_questions"] = metrics.get("skipped_questions", 0) + 1
            new_hints_used = 0
            metrics["retries"] = 0
            next_speech = "Wonderful effort! Let's check out the next one."
        else:  # praise
            new_hints_used = 0
            metrics["retries"] = 0
            encouragements = [
                "Thoughtful answer!", "Nice thinking!", "Great effort!", 
                "Wonderful job explaining!", "That's very clear!"
            ]
            next_speech = random.choice(encouragements)

        # Save Buddy speech to history
        transcript.append({"role": "ai", "text": next_speech, "state": new_session_state})

        return {
            "next_speech": ResponsePolicyLayer.sanitize(next_speech, s_name),
            "transcript": transcript,
            "hints_used_count": new_hints_used,
            "session_state": new_session_state,
            "metrics": metrics,
            "active_hint": active_hint,
            "error": None
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in hint_encourage_praise_node: {e}", exc_info=True)
        return {
            "next_speech": "Let's keep going!",
            "error": str(e)
        }

def next_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Increments question pointer, checking if we route to ask_question or goodbye.
    """
    logger.info("[LangGraph] Executing next_question_node")
    try:
        q_idx = state.get("current_question_index", 0)
        questions = state.get("questions") or []
        transcript = list(state.get("transcript") or [])
        s_name = state.get("student_name", "")

        new_q_idx = q_idx + 1
        next_speech = ""
        new_session_state = "interview"

        if new_q_idx < len(questions):
            next_q = questions[new_q_idx]
            next_q_text = next_q.get("text") or next_q.get("q") or ""
            # Prepend Buddy next speech with previous praise statement
            prev_speech = state.get("next_speech", "")
            next_speech = f"{prev_speech} Let's try this next one. {next_q_text}"
            
            # Since next_speech contains the praise already, replace last transcript entry with compiled version
            if transcript and transcript[-1]["role"] == "ai":
                transcript[-1]["text"] = next_speech
            else:
                transcript.append({"role": "ai", "text": next_speech, "state": "interview"})
        else:
            new_session_state = "GOODBYE"
            next_speech = f"Thank you {s_name}! We have finished all our questions today. You did wonderful! Goodbye!"
            if transcript and transcript[-1]["role"] == "ai":
                transcript[-1]["text"] = f"{state.get('next_speech', '')} {next_speech}"
                transcript[-1]["state"] = "GOODBYE"
            else:
                transcript.append({"role": "ai", "text": next_speech, "state": "GOODBYE"})

        return {
            "current_question_index": new_q_idx,
            "next_speech": ResponsePolicyLayer.sanitize(next_speech, s_name),
            "transcript": transcript,
            "session_state": new_session_state,
            "error": None
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in next_question_node: {e}", exc_info=True)
        return {
            "current_question_index": q_idx + 1,
            "error": str(e)
        }

def goodbye_node(state: InterviewState) -> Dict[str, Any]:
    """
    Finalizes the interview, saving stats.
    """
    logger.info("[LangGraph] Executing goodbye_node")
    return {
        "session_state": "GOODBYE",
        "completion_status": "Completed",
        "error": None
    }

# Build LangGraph State Graph workflow
workflow = StateGraph(InterviewState)

# Add nodes
workflow.add_node("welcome", welcome_node)
workflow.add_node("ask_question", ask_question_node)
workflow.add_node("listen", listen_node)
workflow.add_node("hybrid_intent_detection", hybrid_intent_detection_node)
workflow.add_node("decision", decision_node)
workflow.add_node("hint_encourage_praise", hint_encourage_praise_node)
workflow.add_node("next_question", next_question_node)
workflow.add_node("goodbye", goodbye_node)

# Conditional router logic
def route_welcome_decision(state: InterviewState) -> str:
    if state["session_state"] == "comfort_conv":
        return "welcome"
    return "ask_question"

def route_hint_decision(state: InterviewState) -> str:
    action = state.get("action", "praise")
    if action in ["praise", "skip"]:
        return "next_question"
    return END

def route_next_question(state: InterviewState) -> str:
    q_idx = state["current_question_index"]
    questions = state["questions"]
    if q_idx >= len(questions):
        return "goodbye"
    return END

# Define entry and edges
def route_entry(state: InterviewState) -> str:
    s_state = state.get("session_state", "meet_buddy")
    if s_state in ["meet_buddy", "comfort_conv"]:
        return "welcome"
    return "listen"

workflow.set_conditional_entry_point(
    route_entry,
    {
        "welcome": "welcome",
        "listen": "listen"
    }
)

# Add normal flow links
workflow.add_edge("welcome", END)
workflow.add_edge("ask_question", END)
workflow.add_edge("listen", "hybrid_intent_detection")
workflow.add_edge("hybrid_intent_detection", "decision")
workflow.add_edge("decision", "hint_encourage_praise")

# Add conditional routing paths
workflow.add_conditional_edges(
    "hint_encourage_praise",
    route_hint_decision,
    {
        "next_question": "next_question",
        END: END
    }
)
workflow.add_conditional_edges(
    "next_question",
    route_next_question,
    {
        "goodbye": "goodbye",
        END: END
    }
)
workflow.add_edge("goodbye", END)

# Compile graph
interview_graph = workflow.compile()
