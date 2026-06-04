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

        # 1. Custom Intro
        dynamic_questions.append({
            "q": "Hello! How are you today? Can you tell me about yourself and which class you are in?",
            "skill": "communication",
            "category": "Introduction"
        })

        # 2. Basic class-based warm-up questions
        basic_qs = get_basic_class_questions(sa.student_class)
        dynamic_questions.extend(basic_qs)

        # 3. Assessment-specific questions
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
        if len(dynamic_questions) <= 3:
            dynamic_questions.append({
                "q": "If you could visit any place in the world, where would you go and why?",
                "skill": "creativity",
                "category": "Aspirations"
            })

        return {
            "interview_id": interview.id,
            "student_name": sa.student_name,
            "student_class": sa.student_class,
            "assessment_title": assessment.title,
            "questions": dynamic_questions,
        }

    # ── STEP 2: Student finishes → save transcript → call Groq ───────────────
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

        # Call Groq for AI analysis
        try:
            report = self._call_groq(interview.student_name, payload.answers)
            interview.overall_score       = report.get("overallScore")
            interview.grade               = report.get("grade")
            interview.recommendation      = report.get("recommendation")
            interview.score_communication = report.get("skills", {}).get("communication")
            interview.score_numeracy      = report.get("skills", {}).get("numeracy")
            interview.score_creativity    = report.get("skills", {}).get("creativity")
            interview.score_emotional_iq  = report.get("skills", {}).get("emotionalIntelligence")
            interview.strengths           = report.get("strengths")
            interview.improvements        = report.get("improvements")
            interview.admin_note          = report.get("adminNote")
            interview.summary             = report.get("summary")
            self.db.commit()
            self.db.refresh(interview)
        except Exception as e:
            # Interview is still saved even if AI analysis fails
            print(f"[InterviewService] Groq analysis failed: {e}")

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

    # ── Private: calls Groq API (free) ────────────────────────────────────────
    def _call_groq(self, student_name: str, answers: list) -> dict:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set in your .env file.")

        transcript_text = "\n\n".join(
            f"Q ({a.get('question_category', '')}): {a.get('question', '')}\nA: {a.get('answer', '')}"
            for a in answers
        )

        prompt = f"""You are an expert child psychologist and primary school admission evaluator.
Analyse this interview of a young child (age 5-7) applying for primary school admission.

Student Name: {student_name}
Interview Transcript:
{transcript_text}

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
  "adminNote": "<brief note for the admissions officer>"
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