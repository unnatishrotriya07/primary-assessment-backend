import json
import datetime
import os
import httpx
from typing import Optional, Union
from sqlalchemy.orm import Session

from app.core.models.interview import Interview, InterviewMessage
from app.core.schemas.interview_schema import InterviewSubmitRequest
from app.ai_assessment.interview.manager import InterviewManager
from app.ai_assessment.interview.state import StateManager

GROQ_MODEL = "llama-3.3-70b-versatile"

from app.ai_assessment.prompts import loader

class InterviewService:
    def __init__(self, db: Session):
        self.db = db
        self.manager = InterviewManager(db)
        self.state_mgr = StateManager(db)

    def start_interview(self, token: str, email: str) -> dict:
        return self.manager.start_interview(token, email)

    def save_submission_and_set_evaluating(self, payload: InterviewSubmitRequest) -> Interview:
        return self.manager.save_submission_and_set_evaluating(payload)

    def review_and_approve_report(
        self,
        interview_id: int,
        evaluated_answers: list,
        admin_note: str = None,
        reviewed_by: str = "Teacher"
    ) -> Interview:
        return self.manager.review_and_approve_report(interview_id, evaluated_answers, admin_note, reviewed_by)

    def get_report(self, interview_id: int) -> Interview:
        return self.manager.get_report(interview_id)

    def get_reports_for_assessment(self, assessment_id: int):
        return self.manager.get_reports_for_assessment(assessment_id)

    def update_notes(self, interview_id: int, admin_note: str) -> Interview:
        return self.manager.update_notes(interview_id, admin_note)

    def update_session_state(
        self,
        interview_id: int,
        current_question_index: int,
        session_state: str,
        comfort_index: int,
        raw_answers: list = None,
        network_status: str = "online",
        completion_status: str = "In Progress",
    ) -> Interview:
        return self.state_mgr.update_session_state(
            interview_id, current_question_index, session_state, comfort_index, raw_answers, network_status, completion_status
        )

    def add_message(
        self,
        interview_id: int,
        role: str,
        text: str,
        question_category: str = None,
        sequence_number: int = None,
        question_id: int = None,
        student_response: str = None,
        buddy_response: str = None,
        audio_url: str = None,
        speech_confidence: float = None,
    ) -> InterviewMessage:
        return self.state_mgr.add_message(
            interview_id, role, text, question_category, sequence_number, question_id, student_response, buddy_response, audio_url, speech_confidence
        )

    def process_turn(self, interview_id: int, student_response: str, audio_url: Optional[str] = None) -> dict:
        from app.services.conversation_engine import ConversationEngine
        conv_engine = ConversationEngine(self.db)
        return conv_engine.process_turn(interview_id, student_response, audio_url)

    # ── V1 Evaluation Pipelines (Preserved for compatibility) ──────────────────
    def submit_and_analyse(self, payload: InterviewSubmitRequest) -> Interview:
        interview = self.get_report(payload.interview_id)
        interview.transcript = json.dumps([e.dict() for e in payload.transcript])
        interview.completed_at = datetime.datetime.utcnow()
        interview.status = "Completed"

        sa = self.db.query(StudentAssessment).filter(StudentAssessment.id == interview.student_assessment_id).first()
        if sa:
            sa.status = "Completed"
        self.db.commit()

        qa_eval_context = self.prepare_eval_context(interview, payload.answers)
        report = None
        try:
            report = self._call_ai_and_parse(interview.student_name, qa_eval_context)
        except Exception as e:
            print(f"[InterviewService] AI analysis failed: {e}", flush=True)

        if not report or not isinstance(report, dict):
            try:
                report = self._generate_fallback_report(interview.student_name, qa_eval_context)
            except Exception:
                report = {}

        try:
            overall = report.get("overallScore")
            interview.overall_score = float(overall) if overall is not None else 75.0
            interview.grade = report.get("grade") or "B+"
            interview.recommendation = report.get("recommendation") or "Recommended"
            interview.evaluated_answers = report.get("evaluatedQuestions") or []
            
            skills = report.get("skills") or {}
            def get_skill(keys, default=70.0):
                for k in keys:
                    v = skills.get(k) or report.get(k)
                    if v is not None:
                        return float(v)
                return default

            interview.score_communication = get_skill(["communication", "score_communication"], 70.0)
            interview.score_numeracy      = get_skill(["numeracy", "score_numeracy"], 70.0)
            interview.score_creativity    = get_skill(["creativity", "score_creativity"], 70.0)
            interview.score_emotional_iq  = get_skill(["emotionalIntelligence", "emotional_iq", "score_emotional_iq"], 70.0)
            
            interview.strengths           = report.get("strengths") or "Good verbal response."
            interview.improvements        = report.get("improvements") or "Continue to practice core concepts."
            interview.admin_note          = report.get("adminNote") or report.get("admin_note") or "Completed."
            interview.summary             = report.get("summary") or "Interview completed successfully."
            self.db.commit()
            self.db.refresh(interview)
        except Exception as e:
            print(f"[InterviewService] Error saving report: {e}", flush=True)

        return interview

    def prepare_eval_context(self, interview: Interview, answers: list) -> list:
        from app.core.models.assessment import Assessment
        assessment = self.db.query(Assessment).filter(Assessment.id == interview.assessment_id).first()
        db_questions = assessment.questions if assessment else []
        
        q_map = {}
        for q in db_questions:
            q_map[q.text.strip().lower()] = {
                "expected": q.correct_answer,
                "options": q.options,
                "type": q.question_type or "mcq"
            }
            
        qa_eval_context = []
        for idx, a in enumerate(answers):
            q_text = a.get('question', '').strip()
            q_info = q_map.get(q_text.lower())
            expected = q_info["expected"] if q_info else ""
            q_type = q_info["type"] if q_info else "mcq"
            options = q_info["options"] if q_info else []
            
            qa_eval_context.append({
                "index": idx + 1,
                "question": q_text,
                "student_answer": a.get('answer', ''),
                "expected_answer": expected,
                "options": options,
                "question_type": q_type
            })
        return qa_eval_context

    def evaluate_interview_in_background_v2(self, interview_id: int):
        from app.common.database import SessionLocal
        from app.application import GenerateReportUseCase
        db = SessionLocal()
        try:
            use_case = GenerateReportUseCase(db)
            use_case.execute(interview_id)
        except Exception as e:
            print(f"[Background Task V2] Evaluation failed: {e}", flush=True)
        finally:
            db.close()

    def evaluate_interview_in_background(self, interview_id: int, qa_eval_context: list):
        from app.common.database import SessionLocal
        db = SessionLocal()
        try:
            interview = db.query(Interview).filter(Interview.id == interview_id).first()
            if not interview:
                return
            bg_service = InterviewService(db)
            report = bg_service._call_ai_and_parse(interview.student_name, qa_eval_context)
            if not report:
                report = bg_service._generate_fallback_report(interview.student_name, qa_eval_context)

            overall = report.get("overallScore")
            interview.overall_score = float(overall) if overall is not None else 75.0
            interview.grade = report.get("grade") or "B+"
            interview.recommendation = report.get("recommendation") or "Recommended"
            interview.evaluated_answers = report.get("evaluatedQuestions") or []
            
            skills = report.get("skills") or {}
            def get_skill(keys, default=70.0):
                for k in keys:
                    v = skills.get(k) or report.get(k)
                    if v is not None:
                        return float(v)
                return default

            interview.score_communication = get_skill(["communication", "score_communication"], 70.0)
            interview.score_numeracy      = get_skill(["numeracy", "score_numeracy"], 70.0)
            interview.score_creativity    = get_skill(["creativity", "score_creativity"], 70.0)
            interview.score_emotional_iq  = get_skill(["emotionalIntelligence", "emotional_iq", "score_emotional_iq"], 70.0)
            
            interview.strengths           = report.get("strengths") or "Good verbal response."
            interview.improvements        = report.get("improvements") or "Continue to practice core concepts."
            interview.admin_note          = report.get("adminNote") or report.get("admin_note") or "Completed."
            interview.summary             = report.get("summary") or "Interview completed successfully."
            interview.status = "Completed"
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[Background Task] Error saving background evaluation: {e}", flush=True)
        finally:
            db.close()

    def _call_ai_and_parse(self, student_name: str, answers: list) -> dict:
        import re
        transcript_text = ""
        for item in answers:
            transcript_text += f"Question {item['index']}:\n"
            transcript_text += f"Prompt: {item['question']}\n"
            if item.get('options') and len(item['options']) > 0:
                transcript_text += f"Options: {', '.join(item['options'])}\n"
            transcript_text += f"Expected Answer: {item['expected_answer']}\n"
            transcript_text += f"Question Type: {item['question_type']}\n"
            transcript_text += f"Student's Answer: {item['student_answer']}\n\n"

        prompt = loader.load_evaluate_interview(
            student_name=student_name,
            transcript_text=transcript_text
        )

        system_instruction = loader.load_system_instruction()
        raw_response = None
        
        # 1. Try Groq first
        try:
            print("[InterviewService] Attempting analysis using Groq...", flush=True)
            raw_response = self._call_groq(student_name, answers)
            if isinstance(raw_response, dict):
                return raw_response
        except Exception as e:
            print(f"[InterviewService] Groq analysis failed: {e}", flush=True)

        # 2. Try OpenAI second
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        if not raw_response and openai_api_key:
            try:
                print("[InterviewService] Attempting analysis using OpenAI...", flush=True)
                from app.ai.openai_provider import OpenAIProvider
                openai_prov = OpenAIProvider()
                raw_response = openai_prov.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_mode=True,
                    model_name="gpt-4o-mini"
                )
            except Exception as e:
                print(f"[InterviewService] OpenAI analysis failed: {e}", flush=True)

        # 3. Try Gemini third
        gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        if not raw_response and gemini_api_key:
            try:
                print("[InterviewService] Attempting analysis using Gemini...", flush=True)
                from app.ai.gemini_provider import GeminiProvider
                gemini_prov = GeminiProvider()
                raw_response = gemini_prov.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_mode=True,
                    model_name="gemini-2.0-flash"
                )
            except Exception as e:
                print(f"[InterviewService] Gemini analysis failed: {e}", flush=True)

        # Parse string response if we got one from OpenAI or Gemini
        if raw_response and isinstance(raw_response, str):
            try:
                match = re.search(r"(\{.*\})", raw_response, re.DOTALL)
                clean_json = match.group(1) if match else raw_response
                clean_json = clean_json.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_json)
            except Exception as pe:
                print(f"[InterviewService] Failed to parse AI JSON response: {pe}. Raw: {raw_response}", flush=True)

        print("[InterviewService] Running heuristic fallback report...", flush=True)
        return self._generate_fallback_report(student_name, answers)

    def _call_groq(self, student_name: str, answers: list) -> dict:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set.")
            
        transcript_text = ""
        for item in answers:
            transcript_text += f"Question {item['index']}:\n"
            transcript_text += f"Prompt: {item['question']}\n"
            if item.get('options') and len(item['options']) > 0:
                transcript_text += f"Options: {', '.join(item['options'])}\n"
            transcript_text += f"Expected Answer: {item['expected_answer']}\n"
            transcript_text += f"Question Type: {item['question_type']}\n"
            transcript_text += f"Student's Answer: {item['student_answer']}\n\n"

        prompt = loader.load_evaluate_interview(
            student_name=student_name,
            transcript_text=transcript_text
        )

        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": loader.load_system_instruction()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 4000,
            },
            timeout=30,
        )
        response.raise_for_status()
        raw   = response.json()["choices"][0]["message"]["content"]
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)

    def _generate_fallback_report(self, student_name: str, answers: list) -> dict:
        evaluated_questions = []
        correct_count = 0
        for idx, a in enumerate(answers):
            student_ans = str(a.get("student_answer", "")).strip().lower()
            expected_ans = str(a.get("expected_answer", "")).strip().lower()
            
            is_correct = False
            score_val = 5
            if not student_ans or student_ans in ["silent", "(silent)", "none"]:
                is_correct = False
                score_val = 0
            elif expected_ans:
                if student_ans == expected_ans or expected_ans in student_ans or student_ans in expected_ans:
                    is_correct = True
                    score_val = 10
                else:
                    is_correct = False
                    score_val = 2
            else:
                is_correct = True
                score_val = 8

            if is_correct:
                correct_count += 1

            evaluated_questions.append({
                "index": a.get("index", idx + 1),
                "question": a.get("question", ""),
                "studentAnswer": a.get("student_answer", ""),
                "expectedAnswer": a.get("expected_answer", ""),
                "isCorrect": is_correct,
                "score": score_val,
                "feedback": "Correct response." if is_correct else "Need to review expectations."
            })

        total = len(answers)
        overall_score = (correct_count / total * 100) if total > 0 else 70.0
        
        grade = "B+"
        if overall_score >= 90: grade = "A+"
        elif overall_score >= 80: grade = "A"
        elif overall_score >= 60: grade = "B"
        else: grade = "C"

        return {
            "overallScore": round(overall_score, 1),
            "grade": grade,
            "recommendation": "Continue practice and conceptual reviews.",
            "summary": "Completed oral assessment.",
            "strengths": "Great efforts.",
            "improvements": "Focus on numeracy concepts.",
            "skills": {
                "communication": 75,
                "numeracy": round(overall_score, 1),
                "creativity": 70,
                "emotionalIntelligence": 80
            },
            "evaluatedQuestions": evaluated_questions
        }

from app.core.models.student_assessment import StudentAssessment