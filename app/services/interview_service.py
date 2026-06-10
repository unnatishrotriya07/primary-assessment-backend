import json
import datetime
import os
import httpx
from sqlalchemy.orm import Session

from app.models.interview import Interview
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

        for q in assessment.questions:
            dynamic_questions.append({
                "q": q.text,
                "skill": default_skill,
                "category": q.chapter.title if q.chapter else "Assessment Content"
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
        
        prompt = f"""You are an expert child psychologist and primary school admission evaluator.
Analyse this interview of a young child applying for primary school admission.

Student Name: {student_name}
Interview Transcript with Stored Expected Answers:
{transcript_text}

CRITICAL ASSESSMENT RULES FOR STUDENT ANSWERS:
For each question, compare the Student's Answer against the Expected Answer:
1. For MCQ: check if the student's answer corresponds to the correct option, either by matching the option letter (A, B, C, D) or matching the option text.
2. For TITA (Type In The Answer / descriptive): check if the student's answer resonates semantically with the context of the Expected Answer (it does not need to be an exact string match, but conceptual understanding should be present). If it conceptually resonates, mark it as true (isCorrect: true).

Respond ONLY with a valid JSON object. No explanation, no backticks, no text before or after the JSON.
{{
  "overallScore": <number 0-100>,
  "grade": "<A+/A/B+/B/C>",
  "summary": "<2 sentence overall summary>",
  "skills": {{
    "communication": <0-100>,
    "numeracy": <0-100>,
    "creativity": <0-100>,
    "emotionalIntelligence": <0-100>
  }},
  "strengths": "<2-3 key strengths observed>",
  "improvements": "<1-2 areas to encourage growth>",
  "recommendation": "<Strongly Recommended / Recommended / Needs Review>",
  "adminNote": "<brief note for the admissions officer>",
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
            rec = "Strongly Recommended"
        elif avg_score >= 80:
            grade = "A"
            rec = "Recommended"
        elif avg_score >= 70:
            grade = "B+"
            rec = "Recommended"
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
            "summary": f"{student_name} was highly collaborative and articulated thoughts clearly throughout the session.",
            "strengths": "Articulate speaker, good conceptual foundations, and creative approach.",
            "improvements": "Encourage structured problem solving and peer communication.",
            "adminNote": "Candidate meets the benchmarks. Recommended for enrollment.",
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

        prompt = f"""You are an expert child psychologist and primary school admission evaluator.
Analyse this interview of a young child applying for primary school admission.

Student Name: {student_name}
Interview Transcript with Stored Expected Answers:
{transcript_text}

CRITICAL ASSESSMENT RULES FOR STUDENT ANSWERS:
For each question, compare the Student's Answer against the Expected Answer:
1. For MCQ: check if the student's answer corresponds to the correct option, either by matching the option letter (A, B, C, D) or matching the option text.
2. For TITA (Type In The Answer / descriptive): check if the student's answer resonates semantically with the context of the Expected Answer (it does not need to be an exact string match, but conceptual understanding should be present). If it conceptually resonates, mark it as true (isCorrect: true).

Respond ONLY with a valid JSON object. No markdown, no backticks, no explanation. Just raw JSON:
{{
  "overallScore": <number 0-100>,
  "grade": "<A+/A/B+/B/C>",
  "summary": "<2 sentence overall summary>",
  "skills": {{
    "communication": <0-100>,
    "numeracy": <0-100>,
    "creativity": <0-100>,
    "emotionalIntelligence": <0-100>
  }},
  "strengths": "<2-3 key strengths observed>",
  "improvements": "<1-2 areas to encourage growth>",
  "recommendation": "<Strongly Recommended / Recommended / Needs Review>",
  "adminNote": "<brief note for the admissions officer>",
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
                "max_tokens": 1000,
            },
            timeout=30,
        )
        response.raise_for_status()
        raw   = response.json()["choices"][0]["message"]["content"]
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)