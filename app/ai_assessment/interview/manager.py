import json
import datetime
from sqlalchemy.orm import Session
from app.core.models.interview import Interview, InterviewMessage, ConversationTurn
from app.core.models.student_assessment import StudentAssessment
from app.core.models.assessment import Assessment
from app.core.schemas.interview_schema import InterviewSubmitRequest
from app.ai_assessment.interview.session import SessionBuilder
from app.ai_assessment.interview.state import StateManager

class InterviewManager:
    def __init__(self, db: Session):
        self.db = db
        self.state_mgr = StateManager(db)
        self.session_builder = SessionBuilder(db)

    def start_interview(self, token: str, email: str) -> dict:
        from app.core.services.student_assessment_service import StudentAssessmentService
        sa_service = StudentAssessmentService(self.db)
        
        # Enforce all token validation checks
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

        # 1. Compile assessment if not already done
        from app.core.services.compiler_service import AssessmentCompilerService
        compiler = AssessmentCompilerService(self.db)
        try:
            compiler.compile_assessment(assessment.id)
            self.db.refresh(assessment)
        except Exception as ce:
            print(f"[InterviewManager] Auto-compilation failed: {ce}", flush=True)
            self.db.rollback()

        # Build dynamic list of questions & persona
        dynamic_questions, grade_persona, default_skill = self.session_builder.build_questions_and_persona(sa, assessment, token)

        session_questions = []
        for dq in dynamic_questions:
            session_questions.append({
                "id": dq["id"],
                "text": dq["q"],
                "skill": dq["skill"],
                "category": dq["category"],
                "hints": dq["hints"],
                "expected_concepts": dq["expected_concepts"],
                "followups": dq["followups"],
                "learning_objective": dq["learning_objective"]
            })

        # Session Initialization
        if not interview.session_state_data:
            session_data = {
                "student_name": sa.student_name,
                "student_class": sa.student_class,
                "assessment_id": assessment.id,
                "current_question_index": 0,
                "current_skill": default_skill,
                "current_difficulty": "medium",
                "persona": grade_persona,
                "voice_profile": {"voice": "default_teacher"},
                "memory": {
                    "transcript_summary": "",
                    "concept_coverage": {},
                    "misconceptions": [],
                    "confidence": 1.0,
                    "tone": "neutral",
                    "remaining_questions": [q["text"] for q in session_questions[1:]]
                },
                "hints_used_count": 0,
                "followups_used_count": 0,
                "completed_skills": [],
                "pending_skills": list(set([dq["skill"] for dq in dynamic_questions])),
                "hints_limit": 2,
                "followups_limit": 2,
                "questions": session_questions,
                "history": []
            }
            interview.session_state_data = session_data
            self.db.add(interview)
            self.db.commit()
            self.db.refresh(interview)

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
        interview.raw_answers  = payload.answers
        interview.completed_at = datetime.datetime.utcnow()
        interview.status       = "Transcript Saved"
        interview.language     = "en-US"
        interview.confidence   = 0.95
        interview.audio_references = json.dumps([])
        interview.report_version = "2.0.0"

        # Populate InterviewMessage records for the session
        self.db.query(InterviewMessage).filter(InterviewMessage.interview_id == interview.id).delete()
        self.db.query(ConversationTurn).filter(ConversationTurn.interview_id == interview.id).delete()

        for idx, entry in enumerate(payload.transcript):
            msg = InterviewMessage(
                interview_id=interview.id,
                role=entry.role,
                text=entry.text,
                question_category=entry.question_category,
                sequence_number=idx + 1
            )
            self.db.add(msg)

        # Populate ConversationTurn records
        last_ai_text = None
        for entry in payload.transcript:
            if entry.role == "ai":
                last_ai_text = entry.text
            elif entry.role == "student" and last_ai_text is not None:
                turn = ConversationTurn(
                    interview_id=interview.id,
                    buddy_message=last_ai_text,
                    student_transcript=entry.text
                )
                self.db.add(turn)
                last_ai_text = None
                
        if last_ai_text is not None:
            turn = ConversationTurn(
                interview_id=interview.id,
                buddy_message=last_ai_text,
                student_transcript=""
            )
            self.db.add(turn)

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
        
        total = len(evaluated_answers)
        correct = sum(1 for a in evaluated_answers if a.get("isCorrect"))
        score = (correct / total * 100) if total > 0 else 75.0
        score = round(score, 1)

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
