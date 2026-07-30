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
            
        # 3. I don't know check
        idk_keywords = ["don't know", "dont know", "i forgot", "forgot", "no idea", "not sure", "can't remember", "cant remember"]
        if any(kw in cleaned for kw in idk_keywords):
            return "I_DONT_KNOW"

        # 4. Skip check
        skip_keywords = ["skip", "pass", "next", "move on", "go next", "next question", "already answered", "already gave", "already told", "already gay"]
        if any(kw in cleaned for kw in skip_keywords):
            return "SKIP"

        # 5. Ask Hint check
        hint_keywords = ["hint", "clue", "help me", "give me help", "help please"]
        if any(kw in cleaned for kw in hint_keywords):
            return "ASK_HINT"

        # 6. Confused check
        confused_keywords = ["confused", "don't understand", "dont understand", "what do you mean", "tricky"]
        if any(kw in cleaned for kw in confused_keywords):
            return "CONFUSED"

        return None

# LLM Intent classifier prompt
INTENT_SYSTEM_INSTRUCTION = """You are an educational assessment assistant.
You are evaluating a student's response to a specific question to determine their intent and the accuracy/resonance of their answer.

Examine the Question, the Expected Answer, the Expected Key Concepts, and the Student's Response.

Classify the Student's Response into exactly one of these categories:
- RESONATES_ANSWER: The student attempts to answer, and their response RESONATES with the expected answer or expected key concepts (even if it is only slightly correct, partial, tentative, or half-formed, as long as it shows some correct understanding or is on the right track). Allow for simple vocabulary and spelling/transcription errors (e.g. "already gay" for "already gave", "subtraction problem 5 minutes to you" for "5 minus 2", etc.).
- INCORRECT_ANSWER: The student attempts to answer, but their response is incorrect, does not resonate at all with the expected answer, or shows a major misconception.
- SKIP: The student explicitly asks to skip, pass, move on, go to the next question, or indicates they have already answered / want to proceed.
- ASK_REPEAT: The student explicitly asks to repeat the question or says they didn't hear/understand.
- ASK_HINT: The student asks for help, a hint, or a clue.
- I_DONT_KNOW: The student says "I don't know", "I forgot", "pass", "skip", "no idea", etc.
- CONFUSED: The student says they are confused or don't understand what the question means.
- OFF_TOPIC: The student talks about something completely unrelated to the question or the conversation.
- SILENCE: The response is empty, silent, or contains only meaningless sounds.

Return a raw JSON object with format:
{"intent": "RESONATES_ANSWER" | "INCORRECT_ANSWER" | "SKIP" | "ASK_REPEAT" | "ASK_HINT" | "I_DONT_KNOW" | "CONFUSED" | "OFF_TOPIC" | "SILENCE", "reason": "A brief explanation of why this category was selected"}
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
        student_grade = state.get("student_class", "Grade 3")
        
        transcript = list(state.get("transcript") or [])
        student_resp = state.get("student_response", "")

        # Save student turn in transcript history if they responded
        if c_idx > 0 and student_resp:
            transcript.append({"role": "student", "text": student_resp, "state": "comfort_conv"})

        next_speech = ""
        next_state = "comfort_conv"
        new_c_idx = c_idx

        # Retrieve the first question text to pass to welcome speech if transitioning
        questions = state.get("questions") or []
        first_q = questions[0] if questions else {"q": "Are you ready to share your learning journey?"}
        first_q_text = first_q.get("text") or first_q.get("q") or ""

        # Delegate welcome speech to ConversationManager
        from app.services.conversation_manager import ConversationManager
        conv_mgr = ConversationManager()

        if c_idx == 0:
            if not student_resp or student_resp.lower() in ["", "start", "initiate_interview"]:
                next_speech = conv_mgr.generate_welcome_speech(s_name, student_grade, 0, "", first_q_text, transcript)
                new_c_idx = 1
            else:
                next_speech = conv_mgr.generate_welcome_speech(s_name, student_grade, 1, student_resp, first_q_text, transcript)
                new_c_idx = 2
                next_state = "interview"
        else:
            next_speech = conv_mgr.generate_welcome_speech(s_name, student_grade, 1, student_resp, first_q_text, transcript)
            new_c_idx = 2
            next_state = "interview"

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
            "comfort_index": 2,
            "session_state": "interview",
            "next_speech": "Let's check out our first question together!",
            "error": str(e)
        }

def ask_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Presents the current academic question (fallback/unused in normal workflow).
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
    Detects student intent via Heuristics, falling back to Gemini/Groq Orchestration.
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
        current_q_dict = questions[q_idx] if q_idx < len(questions) else {}
        current_q = current_q_dict.get("text") or current_q_dict.get("q") or ""
        correct_answer = current_q_dict.get("correct_answer", "")
        expected_concepts = current_q_dict.get("expected_concepts", [])
        
        prompt = (
            f"Question: {current_q}\n"
            f"Expected Answer: {correct_answer}\n"
            f"Expected Key Concepts: {expected_concepts}\n"
            f"Student Response: {student_resp}"
        )
        
        raw_res = orchestrator.generate(
            prompt=prompt,
            system_instruction=INTENT_SYSTEM_INSTRUCTION,
            json_mode=True,
            preferred_provider="gemini"
        )
        
        try:
            intent = json.loads(raw_res).get("intent", "RESONATES_ANSWER")
        except Exception:
            intent = "RESONATES_ANSWER"

        logger.info(f"[LangGraph] AI intent classified: {intent}")
        return {"intent": intent, "error": None}
    except Exception as e:
        logger.error(f"[LangGraph] Error in hybrid_intent_detection_node: {e}", exc_info=True)
        return {"intent": "RESONATES_ANSWER", "error": str(e)}

def decision_node(state: InterviewState) -> Dict[str, Any]:
    """
    Planner node: Routes intent to planned action (repeat, hint, praise, skip).
    Enforces maximum 2 conversational assists rule.
    """
    logger.info("[LangGraph] Executing decision_node")
    try:
        intent = state.get("intent", "RESONATES_ANSWER")
        hints_used = state.get("hints_used_count", 0)

        # Enforce Max 2 conversational assists rule
        if hints_used >= 2:
            logger.info(f"[LangGraph] Max assists (2) reached. Forcing skip action.")
            return {"action": "skip", "error": None}

        action = "praise"

        if intent == "ASK_REPEAT":
            action = "repeat"
        elif intent == "SKIP":
            action = "skip"
        elif intent in ["I_DONT_KNOW", "CONFUSED", "ASK_HINT", "INCORRECT_ANSWER"]:
            action = "hint"
        elif intent == "SILENCE":
            action = "encourage_retry"
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
    For repeat/hint/encourage, it generates speech.
    For praise/skip, it delegates speech generation to next_question_node.
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
        student_grade = state.get("student_class", "Grade 3")

        next_speech = state.get("next_speech", "")
        active_hint = state.get("active_hint", None)
        new_hints_used = hints_used
        new_session_state = state.get("session_state", "interview")

        q_text = ""
        q_hints = []
        if q_idx < len(questions):
            q_text = questions[q_idx].get("text") or questions[q_idx].get("q") or ""
            q_hints = questions[q_idx].get("hints") or []

        student_resp = state.get("student_response", "")

        from app.services.conversation_manager import ConversationManager
        conv_mgr = ConversationManager()

        if action in ["praise", "skip"]:
            # Let next_question_node handle speech and history. Just prepare the metrics and reset hints.
            if action == "skip":
                metrics["skipped_questions"] = metrics.get("skipped_questions", 0) + 1
            new_hints_used = 0
            metrics["retries"] = 0
            
            return {
                "hints_used_count": new_hints_used,
                "metrics": metrics,
                "active_hint": None,
                "error": None
            }

        # Handle conversational assists
        if action == "repeat":
            next_speech = conv_mgr.generate_assessment_speech(
                student_name=s_name,
                student_grade=student_grade,
                action="repeat",
                current_question=q_text,
                student_response=student_resp,
                history=transcript
            )
            new_hints_used = hints_used + 1
        elif action == "hint":
            active_hint = q_hints[hints_used] if hints_used < len(q_hints) else "Let's think step by step."
            next_speech = conv_mgr.generate_assessment_speech(
                student_name=s_name,
                student_grade=student_grade,
                action="hint",
                current_question=q_text,
                student_response=student_resp,
                active_hint=active_hint,
                history=transcript
            )
            new_hints_used = hints_used + 1
            new_session_state = "HINT"
        elif action == "encourage_retry":
            metrics["retries"] = metrics.get("retries", 0) + 1
            next_speech = conv_mgr.generate_assessment_speech(
                student_name=s_name,
                student_grade=student_grade,
                action="encourage_retry",
                current_question=q_text,
                student_response=student_resp,
                history=transcript
            )
            new_hints_used = hints_used + 1
        elif action == "encourage_topic":
            next_speech = conv_mgr.generate_assessment_speech(
                student_name=s_name,
                student_grade=student_grade,
                action="encourage_topic",
                current_question=q_text,
                student_response=student_resp,
                history=transcript
            )
            new_hints_used = hints_used + 1

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
    Generates natural transitions using ConversationManager.
    """
    logger.info("[LangGraph] Executing next_question_node")
    try:
        q_idx = state.get("current_question_index", 0)
        questions = state.get("questions") or []
        transcript = list(state.get("transcript") or [])
        s_name = state.get("student_name", "")
        student_grade = state.get("student_class", "Grade 3")
        student_resp = state.get("student_response", "")
        action = state.get("action", "praise")

        q_text = ""
        if q_idx < len(questions):
            q_text = questions[q_idx].get("text") or questions[q_idx].get("q") or ""

        new_q_idx = q_idx + 1
        next_speech = ""
        new_session_state = "interview"

        from app.services.conversation_manager import ConversationManager
        conv_mgr = ConversationManager()

        if new_q_idx < len(questions):
            next_q = questions[new_q_idx]
            next_q_text = next_q.get("text") or next_q.get("q") or ""
            
            # Generate the unified transition speech (praise/skip + next question)
            next_speech = conv_mgr.generate_assessment_speech(
                student_name=s_name,
                student_grade=student_grade,
                action=action,
                current_question=q_text,
                student_response=student_resp,
                next_question=next_q_text,
                history=transcript
            )
            transcript.append({"role": "ai", "text": next_speech, "state": "interview"})
        else:
            new_session_state = "GOODBYE"
            next_speech = conv_mgr.generate_goodbye_speech(s_name, student_grade, transcript)
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
