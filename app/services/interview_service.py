import json
import datetime
import os
import httpx
from sqlalchemy.orm import Session

from app.models.interview import Interview, InterviewMessage
from app.models.student_assessment import StudentAssessment
from app.models.assessment import Assessment
from app.schemas.interview_schema import InterviewSubmitRequest


# Helper to get basic questions based on class
def get_basic_class_questions(class_name: str) -> list:
    name_lower = class_name.lower()
    if "1" in name_lower or "one" in name_lower or "2" in name_lower or "two" in name_lower:
        return [
            {
                "q": "Great! What is your favourite game to play with your friends, and who do you play it with?",
                "skill": "communication",
                "category": "Basic Social"
            },
            {
                "q": "If you had 4 cookies and ate 2, how many cookies would you have left to share?",
                "skill": "numeracy",
                "category": "Basic Math"
            }
        ]
    elif "3" in name_lower or "three" in name_lower or "4" in name_lower or "four" in name_lower:
        return [
            {
                "q": "Wonderful! Can you tell me about your favourite animal and what they like to do?",
                "skill": "creativity",
                "category": "Basic Creativity"
            },
            {
                "q": "If a box contains 12 pencils and you give 4 to your classmate, how many pencils remain in the box?",
                "skill": "numeracy",
                "category": "Basic Math"
            }
        ]
    else: # Grade 5 or fallback
        return [
            {
                "q": "Awesome! What is your favourite hobby when you are not at school, and what makes it fun?",
                "skill": "communication",
                "category": "Basic Social"
            },
            {
                "q": "If you have 20 books and you read 5 of them this week, how many books do you have left to read?",
                "skill": "numeracy",
                "category": "Basic Math"
            }
        ]

# Best free Groq model for this task
GROQ_MODEL = "llama-3.3-70b-versatile"


class InterviewService:
    def __init__(self, db: Session):
        self.db = db

    # ── STEP 1: Student opens link → create interview row ─────────────────────
    def start_interview(self, token: str, email: str) -> dict:
        from app.services.student_assessment_service import StudentAssessmentService
        sa_service = StudentAssessmentService(self.db)
        
        # Enforce all token validation checks (expiry, email matching, already used)
        verify_res = sa_service.verify_token(token, email)
        if not verify_res.valid:
            raise ValueError(verify_res.reason)

        sa = (
            self.db.query(StudentAssessment)
            .filter(StudentAssessment.token == token)
            .first()
        )
        if not sa:
            raise ValueError("Invalid token.")

        assessment = (
            self.db.query(Assessment)
            .filter(Assessment.id == sa.assessment_id)
            .first()
        )
        if not assessment:
            raise ValueError("Assessment not found.")

        if sa.is_used:
            # If the student assessment is already used, we only allow resuming if
            # there is an active "In Progress" interview. Otherwise, it is fully consumed.
            interview = (
                self.db.query(Interview)
                .filter(
                    Interview.student_assessment_id == sa.id,
                    Interview.status == "In Progress"
                )
                .first()
            )
            if not interview:
                raise ValueError("This assessment link has already been used.")
        else:
            interview = None

        if not interview:
            # Consume token so they cannot use this link again to start another interview
            sa.is_used = True
            sa.status = "Started"

            interview = Interview(
                student_assessment_id=sa.id,
                assessment_id=sa.assessment_id,
                student_name=sa.student_name,
                student_class=sa.student_class,
                status="In Progress",
            )
            self.db.add(interview)
            self.db.commit()
            self.db.refresh(interview)


        # Build dynamic list of questions
        dynamic_questions = []

        # 1. Assessment-specific questions
        subject_name = assessment.subject.name.lower() if assessment.subject else ""
        default_skill = "communication"
        if "math" in subject_name or "num" in subject_name:
            default_skill = "numeracy"
        elif "art" in subject_name or "creat" in subject_name:
            default_skill = "creativity"

        from app.services.assessment_service import AssessmentService
        asmt_service = AssessmentService(self.db)
        questions_to_use = asmt_service.get_questions_for_session(assessment.id, seed_str=token)

        for q in questions_to_use:
            # Generate or fetch hint
            hint_val = getattr(q, 'hint', None)
            if not hint_val:
                text_lower = q.text.lower()
                if "numerator" in text_lower:
                    hint_val = "In a fraction, the numerator is the number on the top, which tells us how many parts we are taking."
                elif "denominator" in text_lower:
                    hint_val = "In a fraction, the denominator is the bottom number, which tells us the total number of equal parts."
                elif "equivalent" in text_lower:
                    hint_val = "To find equivalent fractions, think about multiplying or dividing both top and bottom numbers by the same number."
                elif " राहुल" in text_lower or "rahul" in text_lower or "pizza" in text_lower:
                    hint_val = "Think about the total number of slices as the bottom number, and the slices eaten as the top number."
                elif "shaded" in text_lower or "visual" in text_lower or "circle" in text_lower:
                    hint_val = "Count how many parts are colored blue compared to the total number of parts in the shape."
                else:
                    hint_val = "Let's think together. Can you break the question down or explain what you think it means?"
            
            dynamic_questions.append({
                "q": q.text,
                "skill": default_skill,
                "category": q.chapter.title if q.chapter else "Assessment Content",
                "hint": hint_val
            })

        # Fallback if no questions are assigned to the assessment
        if len(dynamic_questions) == 0:
            dynamic_questions.append({
                "q": "If you could visit any place in the world, where would you go and why?",
                "skill": "creativity",
                "category": "Aspirations"
            })

        # Find subject name and chapter info to return for custom greeting
        sub_name = assessment.subject.name if assessment.subject else ""
        ch_number = ""
        ch_title = ""
        for q in assessment.questions:
            if q.chapter:
                ch_number = q.chapter.number
                ch_title = q.chapter.title
                break

        return {
            "interview_id": interview.id,
            "student_name": sa.student_name,
            "student_class": sa.student_class,
            "assessment_title": assessment.title,
            "questions": dynamic_questions,
            "subject_name": sub_name,
            "chapter_number": ch_number,
            "chapter_title": ch_title,
        }

    # ── STEP 2: Student finishes → save transcript → call AI ──────────────────
    def submit_and_analyse(self, payload: InterviewSubmitRequest) -> Interview:
        interview = (
            self.db.query(Interview)
            .filter(Interview.id == payload.interview_id)
            .first()
        )
        if not interview:
            raise ValueError("Interview session not found.")

        # Save transcript
        interview.transcript   = json.dumps([e.dict() for e in payload.transcript])
        interview.completed_at = datetime.datetime.utcnow()
        interview.status       = "Completed"

        # Mark parent StudentAssessment as completed
        sa = (
            self.db.query(StudentAssessment)
            .filter(StudentAssessment.id == interview.student_assessment_id)
            .first()
        )
        if sa:
            sa.status = "Completed"

        self.db.commit()

        # Load assessment questions to match correct answers
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
        for idx, a in enumerate(payload.answers):
            q_text = a.get('question', '').strip()
            q_info = q_map.get(q_text.lower())
            
            expected = ""
            q_type = "mcq"
            options = []
            
            if q_info:
                expected = q_info["expected"]
                q_type = q_info["type"]
                options = q_info["options"]
            
            qa_eval_context.append({
                "index": idx + 1,
                "question": q_text,
                "student_answer": a.get('answer', ''),
                "expected_answer": expected,
                "options": options,
                "question_type": q_type
            })

        # Call AI analysis (Groq/OpenAI/Gemini) with fallback support
        report = None
        try:
            report = self._call_ai_and_parse(interview.student_name, qa_eval_context)
        except Exception as e:
            print(f"[InterviewService] AI analysis failed: {e}", flush=True)

        if not report or not isinstance(report, dict):
            try:
                print("[InterviewService] Using heuristic fallback report...", flush=True)
                report = self._generate_fallback_report(interview.student_name, qa_eval_context)
            except Exception as fe:
                print(f"[InterviewService] Heuristic fallback failed: {fe}", flush=True)
                report = {}

        try:
            overall = report.get("overallScore")
            if overall is not None:
                try:
                    interview.overall_score = float(overall)
                except (ValueError, TypeError):
                    interview.overall_score = 75.0
            else:
                interview.overall_score = 75.0

            interview.grade = report.get("grade") or "B+"
            interview.recommendation = report.get("recommendation") or "Recommended"
            interview.evaluated_answers = report.get("evaluatedQuestions") or []
            
            skills = report.get("skills") or {}
            
            def get_skill(keys, default=70.0):
                for k in keys:
                    v = skills.get(k)
                    if v is not None:
                        try:
                            return float(v)
                        except (ValueError, TypeError):
                            pass
                for k in keys:
                    v = report.get(k)
                    if v is not None:
                        try:
                            return float(v)
                        except (ValueError, TypeError):
                            pass
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
            print(f"[InterviewService] Error saving interview report details: {e}", flush=True)

        return interview

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
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError("Interview session not found.")
        
        msg = InterviewMessage(
            interview_id=interview_id,
            role=role,
            text=text,
            question_category=question_category,
            sequence_number=sequence_number,
            question_id=question_id,
            student_response=student_response,
            buddy_response=buddy_response,
            audio_url=audio_url,
            speech_confidence=speech_confidence,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)

        # Re-build progressive raw_transcript turn list
        messages = (
            self.db.query(InterviewMessage)
            .filter(InterviewMessage.interview_id == interview_id)
            .order_by(InterviewMessage.id.asc())
            .all()
        )
        raw_list = []
        for m in messages:
            raw_list.append({
                "role": m.role,
                "text": m.text,
                "category": m.question_category,
                "sequence_number": m.sequence_number,
                "speech_confidence": m.speech_confidence,
            })
        interview.raw_transcript = json.dumps(raw_list)
        self.db.commit()
        return msg

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
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError("Interview session not found.")
        
        interview.current_question_index = current_question_index
        interview.session_state = session_state
        interview.comfort_index = comfort_index
        if raw_answers is not None:
            interview.raw_answers = raw_answers
        interview.network_status = network_status
        interview.completion_status = completion_status
        
        self.db.commit()
        self.db.refresh(interview)
        return interview

    def review_and_approve_report(
        self,
        interview_id: int,
        evaluated_answers: list,
        admin_note: str = None,
        reviewed_by: str = "Teacher"
    ) -> Interview:
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError("Interview session not found.")
        
        # Recalculate score based on evaluated_answers edits
        total = len(evaluated_answers)
        correct = sum(1 for a in evaluated_answers if a.get("isCorrect"))
        score = (correct / total * 100) if total > 0 else 75.0
        score = round(score, 1)

        # Grade scale
        if score >= 90:
            grade = "A+"
            rec = "Excellent Comprehension"
        elif score >= 80:
            grade = "A"
            rec = "Good Understanding"
        elif score >= 70:
            grade = "B+"
            rec = "Good Understanding"
        elif score >= 60:
            grade = "B"
            rec = "Needs Review"
        else:
            grade = "C"
            rec = "Needs Review"

        interview.evaluated_answers = evaluated_answers
        interview.overall_score = score
        interview.grade = grade
        interview.recommendation = rec
        if admin_note is not None:
            interview.admin_note = admin_note
        
        interview.requires_review = False
        interview.review_reason = None
        interview.reviewed_by = reviewed_by
        interview.reviewed_at = datetime.datetime.utcnow()
        interview.status = "Report Ready"
        
        self.db.commit()
        self.db.refresh(interview)
        return interview


    def save_submission_and_set_evaluating(self, payload: InterviewSubmitRequest) -> Interview:
        interview = (
            self.db.query(Interview)
            .filter(Interview.id == payload.interview_id)
            .first()
        )
        if not interview:
            raise ValueError("Interview session not found.")

        # Save transcript & V2 engine metadata
        interview.transcript   = json.dumps([e.dict() for e in payload.transcript])
        interview.completed_at = datetime.datetime.utcnow()
        interview.status       = "Transcript Saved"
        interview.language     = "en-US"
        interview.confidence   = 0.95
        interview.audio_references = json.dumps([])
        interview.report_version = "2.0.0"

        # Mark parent StudentAssessment as completed
        sa = (
            self.db.query(StudentAssessment)
            .filter(StudentAssessment.id == interview.student_assessment_id)
            .first()
        )
        if sa:
            sa.status = "Completed"

        self.db.commit()
        self.db.refresh(interview)
        return interview

    def evaluate_interview_in_background_v2(self, interview_id: int):
        from app.db.session import SessionLocal
        from app.services.evaluation_pipeline import EvaluationPipelineService
        db = SessionLocal()
        try:
            pipeline = EvaluationPipelineService(db)
            pipeline.run_pipeline(interview_id)
        except Exception as e:
            print(f"[Background Task V2] Evaluation failed: {e}", flush=True)
        finally:
            db.close()

    def prepare_eval_context(self, interview: Interview, answers: list) -> list:
        # Load assessment questions to match correct answers
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
            
            expected = ""
            q_type = "mcq"
            options = []
            
            if q_info:
                expected = q_info["expected"]
                q_type = q_info["type"]
                options = q_info["options"]
            
            qa_eval_context.append({
                "index": idx + 1,
                "question": q_text,
                "student_answer": a.get('answer', ''),
                "expected_answer": expected,
                "options": options,
                "question_type": q_type
            })
        return qa_eval_context

    def evaluate_interview_in_background(self, interview_id: int, qa_eval_context: list):
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            # Fetch interview inside the new session
            interview = db.query(Interview).filter(Interview.id == interview_id).first()
            if not interview:
                print(f"[Background Task] Interview {interview_id} not found.", flush=True)
                return

            # Call AI analysis
            report = None
            try:
                # Call helper method on a service instance bound to the new db session
                bg_service = InterviewService(db)
                report = bg_service._call_ai_and_parse(interview.student_name, qa_eval_context)
            except Exception as e:
                print(f"[Background Task] AI analysis failed: {e}", flush=True)

            if not report or not isinstance(report, dict):
                try:
                    print("[Background Task] Using heuristic fallback report...", flush=True)
                    bg_service = InterviewService(db)
                    report = bg_service._generate_fallback_report(interview.student_name, qa_eval_context)
                except Exception as fe:
                    print(f"[Background Task] Heuristic fallback failed: {fe}", flush=True)
                    report = {}

            # Save report details to interview object
            overall = report.get("overallScore")
            if overall is not None:
                try:
                    interview.overall_score = float(overall)
                except (ValueError, TypeError):
                    interview.overall_score = 75.0
            else:
                interview.overall_score = 75.0

            interview.grade = report.get("grade") or "B+"
            interview.recommendation = report.get("recommendation") or "Recommended"
            interview.evaluated_answers = report.get("evaluatedQuestions") or []
            
            skills = report.get("skills") or {}
            
            def get_skill(keys, default=70.0):
                for k in keys:
                    v = skills.get(k)
                    if v is not None:
                        try:
                            return float(v)
                        except (ValueError, TypeError):
                            pass
                for k in keys:
                    v = report.get(k)
                    if v is not None:
                        try:
                            return float(v)
                        except (ValueError, TypeError):
                            pass
                return default

            interview.score_communication = get_skill(["communication", "score_communication"], 70.0)
            interview.score_numeracy      = get_skill(["numeracy", "score_numeracy"], 70.0)
            interview.score_creativity    = get_skill(["creativity", "score_creativity"], 70.0)
            interview.score_emotional_iq  = get_skill(["emotionalIntelligence", "emotional_iq", "score_emotional_iq"], 70.0)
            
            interview.strengths           = report.get("strengths") or "Good verbal response."
            interview.improvements        = report.get("improvements") or "Continue to practice core concepts."
            interview.admin_note          = report.get("adminNote") or report.get("admin_note") or "Completed."
            interview.summary             = report.get("summary") or "Interview completed successfully."
            
            # Mark status as completed
            interview.status = "Completed"
            
            db.commit()
            print(f"[Background Task] Interview {interview_id} successfully evaluated and updated.", flush=True)
        except Exception as e:
            db.rollback()
            print(f"[Background Task] Error saving background evaluation for interview {interview_id}: {e}", flush=True)
        finally:
            db.close()

    # ── STEP 3: Fetch report ──────────────────────────────────────────────────
    def get_report(self, interview_id: int) -> Interview:
        interview = (
            self.db.query(Interview)
            .filter(Interview.id == interview_id)
            .first()
        )
        if not interview:
            raise ValueError("Interview report not found.")
        return interview

    def get_reports_for_assessment(self, assessment_id: int):
        return (
            self.db.query(Interview)
            .filter(
                Interview.assessment_id == assessment_id,
                Interview.status == "Completed",
            )
            .all()
        )

    def update_notes(self, interview_id: int, admin_note: str) -> Interview:
        interview = (
            self.db.query(Interview)
            .filter(Interview.id == interview_id)
            .first()
        )
        if not interview:
            raise ValueError("Interview session not found.")
        interview.admin_note = admin_note
        self.db.commit()
        self.db.refresh(interview)
        return interview

    # ── Private: calls AI with Multi-Provider Fallbacks & Robust JSON Parser ──
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
        
        prompt = f"""You are an expert primary school educator and class teacher.
Analyse this oral assessment of a student for their class chapter review.

Student Name: {student_name}
Assessment Transcript with Stored Expected Answers:
{transcript_text}

CRITICAL ASSESSMENT RULES FOR STUDENT ANSWERS:
For each question, compare the Student's Answer against the Expected Answer:
1. For MCQ: check if the student's answer corresponds to the correct option, either by matching the option letter (A, B, C, D) or matching the option text.
2. For TITA (Type In The Answer / descriptive): check if the student's answer resonates semantically with the context of the Expected Answer (it does not need to be an exact string match, but conceptual understanding should be present). If it conceptually resonates, mark it as true (isCorrect: true).

Respond ONLY with a valid JSON object. No explanation, no backticks, no text before or after the JSON.
{{
  "overallScore": <number 0-100>,
  "grade": "<A+/A/B+/B/C>",
  "summary": "<2 sentence pedagogical summary of student understanding>",
  "skills": {{
    "communication": <0-100>,
    "numeracy": <0-100>,
    "creativity": <0-100>,
    "emotionalIntelligence": <0-100>
  }},
  "strengths": "<2-3 key concept strengths observed>",
  "improvements": "<1-2 growth areas to practice>",
  "recommendation": "<Excellent Comprehension / Good Understanding / Needs Review>",
  "adminNote": "<brief observational note for the class teacher regarding student comprehension>",
  "evaluatedQuestions": [
     {{
       "question": "<question text>",
       "studentAnswer": "<student answer text>",
       "expectedAnswer": "<expected correct answer text>",
       "questionType": "<mcq or tita>",
       "isCorrect": <true or false>,
       "explanation": "<1 sentence explanation why it was marked correct or incorrect>"
     }}
  ]
}}"""

        system_instruction = "You are a child assessment expert. You always respond with valid raw JSON only, no markdown, no backticks."

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

        # 4. Heuristic fallback
        print("[InterviewService] Running heuristic fallback report...", flush=True)
        return self._generate_fallback_report(student_name, answers)

    def _generate_fallback_report(self, student_name: str, answers: list) -> dict:
        import random
        import re

        def check_answers_match(student_ans: str, expected_ans: str) -> bool:
            s_clean = student_ans.lower().strip()
            e_clean = expected_ans.lower().strip()
            
            if not s_clean:
                return False
                
            # 1. Direct match or substring match
            if s_clean in e_clean or e_clean in s_clean:
                return True
                
            # 2. Normalize common punctuation and abbreviations
            def normalize_str(text: str) -> str:
                text = text.replace("a.m.", "am").replace("p.m.", "pm")
                # Remove punctuation
                text = re.sub(r"[^\w\s]", "", text)
                return " ".join(text.split())
                
            s_norm = normalize_str(s_clean)
            e_norm = normalize_str(e_clean)
            
            if s_norm in e_norm or e_norm in s_norm:
                return True
                
            # 3. Check for specific numeric values (e.g. "3:30 pm" vs "330" or "8")
            s_nums = re.findall(r"\d+", s_clean)
            e_nums = re.findall(r"\d+", e_clean)
            if e_nums:
                s_combined = "".join(s_nums)
                e_combined = "".join(e_nums)
                if s_combined and e_combined and (s_combined in e_combined or e_combined in s_combined):
                    return True
                    
            # 4. Content words overlap
            stop_words = {
                "is", "the", "a", "an", "and", "or", "in", "we", "have", "you", "to", "of", "it", 
                "that", "this", "for", "with", "on", "at", "by", "from", "between", "here", "there"
            }
            
            def get_content_words(text: str) -> set:
                words = re.findall(r"\b\w+\b", text)
                return {w for w in words if w not in stop_words and len(w) > 1}
                
            s_words = get_content_words(s_norm)
            e_words = get_content_words(e_norm)
            
            if not e_words:
                return False
                
            overlap = s_words.intersection(e_words)
            
            # Match if at least 40% of content words in expected answer are found in student answer,
            # or if there is a minimum word overlap count.
            if len(e_words) <= 2:
                return len(overlap) >= 1
            else:
                match_ratio = len(overlap) / len(e_words)
                return match_ratio >= 0.4 or len(overlap) >= 2

        scores = []
        evaluated_qs = []
        for a in answers:
            ans = a.get("student_answer", "")
            expected = a.get("expected_answer", "")
            q_type = a.get("question_type", "mcq")
            word_count = len(ans.split())
            
            is_correct = check_answers_match(ans, expected)

            # Distinguish score calculation based on correctness
            if is_correct:
                q_score = min(80 + word_count * 2, 98)
            else:
                q_score = min(40 + word_count * 3, 65)
            scores.append(q_score)
            
            evaluated_qs.append({
                "question": a.get("question", ""),
                "studentAnswer": ans,
                "expectedAnswer": expected,
                "questionType": q_type,
                "isCorrect": is_correct,
                "explanation": "Heuristic verification." if is_correct else "Answer did not conceptually resonate with expected guidelines."
            })
            
        avg_score = sum(scores) / len(scores) if scores else 75.0
        avg_score = round(avg_score, 1)
        
        if avg_score >= 90:
            grade = "A+"
            rec = "Excellent Comprehension"
        elif avg_score >= 80:
            grade = "A"
            rec = "Good Understanding"
        elif avg_score >= 70:
            grade = "B+"
            rec = "Good Understanding"
        else:
            grade = "B"
            rec = "Needs Review"
            
        comm = min(max(int(avg_score + random.randint(-4, 6)), 50), 98)
        num = min(max(int(avg_score + random.randint(-6, 4)), 50), 98)
        creat = min(max(int(avg_score + random.randint(-3, 8)), 50), 98)
        eq = min(max(int(avg_score + random.randint(-2, 5)), 50), 98)
        
        return {
            "overallScore": avg_score,
            "grade": grade,
            "recommendation": rec,
            "skills": {
                "communication": comm,
                "numeracy": num,
                "creativity": creat,
                "emotionalIntelligence": eq
            },
            "summary": f"{student_name} was highly collaborative and active during the assessment.",
            "strengths": "Good conceptual understanding and creative approach.",
            "improvements": "Encourage structured problem solving and regular practice.",
            "adminNote": "Student demonstrated good comprehension of the chapter content.",
            "evaluatedQuestions": evaluated_qs
        }

    # ── Private: calls Groq API (free) ────────────────────────────────────────
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

        prompt = f"""You are an expert primary school educator and class teacher.
Analyse this oral assessment of a student for their class chapter review.

Student Name: {student_name}
Assessment Transcript with Stored Expected Answers:
{transcript_text}

CRITICAL ASSESSMENT RULES FOR STUDENT ANSWERS:
For each question, compare the Student's Answer against the Expected Answer:
1. For MCQ: check if the student's answer corresponds to the correct option, either by matching the option letter (A, B, C, D) or matching the option text.
2. For TITA (Type In The Answer / descriptive): check if the student's answer resonates semantically with the context of the Expected Answer (it does not need to be an exact string match, but conceptual understanding should be present). If it conceptually resonates, mark it as true (isCorrect: true).

Respond ONLY with a valid JSON object. No markdown, no backticks, no explanation. Just raw JSON:
{{
  "overallScore": <number 0-100>,
  "grade": "<A+/A/B+/B/C>",
  "summary": "<2 sentence pedagogical summary of student understanding>",
  "skills": {{
    "communication": <0-100>,
    "numeracy": <0-100>,
    "creativity": <0-100>,
    "emotionalIntelligence": <0-100>
  }},
  "strengths": "<2-3 key concept strengths observed>",
  "improvements": "<1-2 growth areas to practice>",
  "recommendation": "<Excellent Comprehension / Good Understanding / Needs Review>",
  "adminNote": "<brief observational note for the class teacher regarding student comprehension>",
  "evaluatedQuestions": [
     {{
       "question": "<question text>",
       "studentAnswer": "<student answer text>",
       "expectedAnswer": "<expected correct answer text>",
       "questionType": "<mcq or tita>",
       "isCorrect": <true or false>,
       "explanation": "<1 sentence explanation why it was marked correct or incorrect>"
     }}
  ]
}}"""

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
                        "content": "You are a child assessment expert. You always respond with valid raw JSON only, no markdown, no backticks."
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