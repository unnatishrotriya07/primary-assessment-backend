import datetime
import uuid
import logging
import urllib.parse
from sqlalchemy.orm import Session

from app.models.student_assessment import StudentAssessment
from app.models.assessment import Assessment
from app.schemas.student_assessment_schema import (
    StudentAssessmentCreate, StudentAssessmentResponse, StudentAssessmentVerifyResponse
)
from app.core.exceptions import EntityNotFoundException
from app.services.assessment_service import AssessmentService
from app.services.email_service import EmailService
from app.core.config import settings

logger = logging.getLogger(__name__)

class StudentAssessmentService:
    def __init__(self, db: Session):
        self.db = db

    def assign_assessment(self, schema: StudentAssessmentCreate, frontend_url: str = None) -> StudentAssessmentResponse:
        # Check if the base assessment exists
        asmt = self.db.query(Assessment).filter(Assessment.id == schema.assessment_id).first()
        if not asmt:
            raise EntityNotFoundException("Assessment", str(schema.assessment_id))

        # Generate unique single-use token and 24h expiration
        token = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow()
        expires_at = created_at + datetime.timedelta(hours=24)

        # Create record
        sa = StudentAssessment(
            assessment_id=schema.assessment_id,
            student_name=schema.student_name,
            student_class=schema.student_class,
            date_of_birth=schema.date_of_birth,
            student_email=schema.student_email,
            contact=schema.contact,
            token=token,
            created_at=created_at,
            expires_at=expires_at,
            is_used=False,
            status="Pending"
        )
        self.db.add(sa)
        self.db.commit()
        self.db.refresh(sa)

        # Generate link
        encoded_email = urllib.parse.quote(schema.student_email)
        base_frontend_url = (frontend_url or settings.FRONTEND_URL).rstrip("/")
        link = f"{base_frontend_url}/assessment/verify?token={token}&email={encoded_email}"

        # Generate simulated email body
        email_content = (
            f"Subject: You've been assigned an assessment: {asmt.title}\n"
            f"To: {schema.student_email}\n\n"
            f"Dear {schema.student_name},\n\n"
            f"Your teacher has assigned you the assessment \"{asmt.title}\" for class {schema.student_class}.\n\n"
            f"Please click the link below to access your assessment. Note that this link is only active for 24 hours "
            f"and can only be accessed once. You will be required to authenticate with your Google account "
            f"({schema.student_email}) to verify your identity.\n\n"
            f"Assessment Access Link:\n"
            f"{link}\n\n"
            f"Expiration Date: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
            f"Good luck!\n"
        )

        logger.info(f"\n================ SIMULATED EMAIL DISPATCH =================\n{email_content}===========================================================")

        # Dispatch email via SendGrid (handles config checks and logs internal failures gracefully)
        email_service = EmailService()
        email_service.send_assessment_invitation(
            student_name=schema.student_name,
            student_email=schema.student_email,
            assessment_title=asmt.title,
            link=link,
            expires_at_str=expires_at.strftime('%Y-%m-%d %H:%M:%S')
        )

        # Map to response schema
        return StudentAssessmentResponse(
            id=sa.id,
            assessment_id=sa.assessment_id,
            student_name=sa.student_name,
            student_class=sa.student_class,
            date_of_birth=sa.date_of_birth,
            student_email=sa.student_email,
            contact=sa.contact,
            token=sa.token,
            created_at=sa.created_at,
            expires_at=sa.expires_at,
            is_used=sa.is_used,
            session_id=sa.session_id,
            status=sa.status,
            assessment_link=link,
            email_content=email_content
        )

    def verify_token(self, token: str, email: str) -> StudentAssessmentVerifyResponse:
        sa = self.db.query(StudentAssessment).filter(StudentAssessment.token == token).first()
        if not sa:
            return StudentAssessmentVerifyResponse(valid=False, reason="Invalid token.")

        if sa.status == "Completed":
            return StudentAssessmentVerifyResponse(valid=False, reason="This assessment link has already been used and completed.")

        if sa.is_used and sa.status != "Started":
            return StudentAssessmentVerifyResponse(valid=False, reason="This assessment link has already been used.")

        now = datetime.datetime.utcnow()
        if sa.expires_at < now:
            sa.status = "Expired"
            self.db.commit()
            return StudentAssessmentVerifyResponse(valid=False, reason="This assessment link has expired (active for 24 hours only).")

        # Compare email case-insensitively
        if sa.student_email.strip().lower() != email.strip().lower():
            return StudentAssessmentVerifyResponse(valid=False, reason="Email mismatch. This link was created for another student.")

        return StudentAssessmentVerifyResponse(
            valid=True,
            student_name=sa.student_name,
            student_email=sa.student_email,
            assessment_title=sa.assessment.title,
            subject_name=sa.assessment.subject.name if sa.assessment.subject else "Unknown",
            class_name=sa.assessment.target_class.name if sa.assessment.target_class else "Unknown"
        )

    def start_session_by_token(self, token: str, email: str) -> dict:
        verify_res = self.verify_token(token, email)
        if not verify_res.valid:
            raise ValueError(verify_res.reason)

        sa = self.db.query(StudentAssessment).filter(StudentAssessment.token == token).first()
        
        if sa.is_used:
            raise ValueError("This assessment link has already been used.")
        
        # Generate session id
        session_id = f"asmt_{sa.assessment_id}_{uuid.uuid4().hex[:8]}"

        # Consume token and update session info
        sa.is_used = True
        sa.session_id = session_id
        sa.status = "Started"
        self.db.commit()

        # Load questions for the assessment
        asmt_service = AssessmentService(self.db)
        questions = asmt_service.get_questions_for_session(sa.assessment_id)

        sanitized_questions = []
        for q in questions:
            sanitized_questions.append({
                "id": q.id,
                "text": q.text,
                "options": q.options,
                "difficulty": q.difficulty,
                "cognitiveLevel": q.cognitive_level,
                "subjectId": q.subject_id,
                "chapterId": q.chapter_id
            })

        return {
            "sessionId": session_id,
            "assessment": {
                "id": sa.assessment.id,
                "title": sa.assessment.title,
                "subjectId": sa.assessment.subject_id,
                "classId": sa.assessment.class_id,
                "status": sa.assessment.status,
                "date": sa.assessment.date,
                "questionsCount": sa.assessment.questions_count,
                "questions": sanitized_questions
            }
        }
