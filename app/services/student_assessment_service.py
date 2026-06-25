import datetime
import uuid
import logging
import urllib.parse
from sqlalchemy.orm import Session

from typing import List
from app.models.student_assessment import StudentAssessment
from app.models.assessment import Assessment
from app.schemas.student_assessment_schema import (
    StudentAssessmentCreate, StudentAssessmentResponse, StudentAssessmentVerifyResponse, StudentAssessmentBulkCreate
)
from app.core.exceptions import EntityNotFoundException
from app.services.assessment_service import AssessmentService
from app.services.email_service import EmailService
from app.core.config import settings

logger = logging.getLogger(__name__)

class StudentAssessmentService:
    def __init__(self, db: Session):
        self.db = db

    def assign_assessment(self, schema: StudentAssessmentCreate, tenant_id: str = None, frontend_url: str = None) -> StudentAssessmentResponse:
        # Check if the base assessment exists
        asmt_query = self.db.query(Assessment).filter(Assessment.id == schema.assessment_id)
        if tenant_id is not None:
            asmt_query = asmt_query.filter(Assessment.tenant_id == tenant_id)
        asmt = asmt_query.first()
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
            status="Pending",
            tenant_id=tenant_id
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
        
        if sa.is_used and sa.status != "Started":
            raise ValueError("This assessment link has already been used.")
        
        # Generate session id if not already present
        session_id = sa.session_id or f"asmt_{sa.assessment_id}_{uuid.uuid4().hex[:8]}"

        # Consume token and update session info
        sa.is_used = True
        sa.session_id = session_id
        sa.status = "Started"
        self.db.commit()

        # Load questions for the assessment
        asmt_service = AssessmentService(self.db)
        questions = asmt_service.get_questions_for_session(sa.assessment_id, seed_str=sa.token)

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

    def assign_assessment_bulk(self, schema: StudentAssessmentBulkCreate, tenant_id: str = None, frontend_url: str = None) -> List[StudentAssessmentResponse]:
        # Check if the base assessment exists
        asmt_query = self.db.query(Assessment).filter(Assessment.id == schema.assessment_id)
        if tenant_id is not None:
            asmt_query = asmt_query.filter(Assessment.tenant_id == tenant_id)
        asmt = asmt_query.first()
        if not asmt:
            raise EntityNotFoundException("Assessment", str(schema.assessment_id))

        # Fetch the target class name
        from app.models.class_model import Class
        cls = self.db.query(Class).filter(Class.id == asmt.class_id).first()
        class_name = f"{cls.name} ({cls.section})" if cls else "Unknown Class"

        # Fetch the student records
        from app.models.student import Student
        student_query = self.db.query(Student).filter(Student.id.in_(schema.student_ids))
        if tenant_id is not None:
            student_query = student_query.filter(Student.tenant_id == tenant_id)
        students = student_query.all()
        if not students:
            raise ValueError("No valid students found for the provided IDs.")

        responses = []
        base_frontend_url = (frontend_url or settings.FRONTEND_URL).rstrip("/")

        for student in students:
            # Generate unique single-use token and 24h expiration
            token = str(uuid.uuid4())
            created_at = datetime.datetime.utcnow()
            expires_at = created_at + datetime.timedelta(hours=24)

            # Create record
            sa = StudentAssessment(
                assessment_id=schema.assessment_id,
                student_name=student.name,
                student_class=class_name,
                date_of_birth="2010-01-01",  # Fallback DOB since student table lacks it
                student_email=student.email,
                contact=student.contact_number or "0000000000",  # Fallback contact number
                token=token,
                created_at=created_at,
                expires_at=expires_at,
                is_used=False,
                status="Pending",
                tenant_id=tenant_id
            )
            self.db.add(sa)
            self.db.commit()
            self.db.refresh(sa)

            # Generate link
            encoded_email = urllib.parse.quote(student.email)
            link = f"{base_frontend_url}/assessment/verify?token={token}&email={encoded_email}"

            # Generate simulated email body
            email_content = (
                f"Subject: You've been assigned an assessment: {asmt.title}\n"
                f"To: {student.email}\n\n"
                f"Dear {student.name},\n\n"
                f"Your teacher has assigned you the assessment \"{asmt.title}\" for class {class_name}.\n\n"
                f"Please click the link below to access your assessment. Note that this link is only active for 24 hours "
                f"and can only be accessed once. You will be required to authenticate with your Google account "
                f"({student.email}) to verify your identity.\n\n"
                f"Assessment Access Link:\n"
                f"{link}\n\n"
                f"Expiration Date: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                f"Good luck!\n"
            )

            logger.info(f"\n================ SIMULATED EMAIL DISPATCH =================\n{email_content}===========================================================")

            # Dispatch email via SendGrid
            email_service = EmailService()
            email_service.send_assessment_invitation(
                student_name=student.name,
                student_email=student.email,
                assessment_title=asmt.title,
                link=link,
                expires_at_str=expires_at.strftime('%Y-%m-%d %H:%M:%S')
            )

            responses.append(
                StudentAssessmentResponse(
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
            )

        return responses

    def join_verify(self, schema: "StudentJoinVerifyRequest", frontend_url: str = None) -> StudentAssessmentResponse:
        # 1. Fetch the assessment
        asmt = self.db.query(Assessment).filter(Assessment.id == schema.assessment_id).first()
        if not asmt:
            raise EntityNotFoundException("Assessment", str(schema.assessment_id))

        # 2. Check 24 hour expiration
        if asmt.created_at:
            import datetime
            time_elapsed = datetime.datetime.utcnow() - asmt.created_at
            if time_elapsed.total_seconds() > 24 * 3600:
                raise ValueError("This assessment link has expired (valid for 24 hours only).")

        # 3. Retrieve student in class with matching scholar number
        from app.models.student import Student
        student = (
            self.db.query(Student)
            .filter(Student.class_id == asmt.class_id)
            .filter(Student.scholar_number == schema.scholar_number.strip())
            .first()
        )
        if not student:
            raise ValueError("Student details not found. Please verify your Scholar ID and Class.")

        # Check name case-insensitively
        if student.name.strip().lower() != schema.student_name.strip().lower():
            raise ValueError("Verification failed. The student name does not match the Scholar ID in this class.")

        # 4. Check if student already has a StudentAssessment record for this assessment
        existing_sa = (
            self.db.query(StudentAssessment)
            .filter(StudentAssessment.assessment_id == asmt.id)
            .filter(StudentAssessment.student_email == student.email)
            .first()
        )

        if existing_sa:
            if existing_sa.status == "Completed":
                raise ValueError("You have already completed this assessment.")
            
            # Return existing session token
            encoded_email = urllib.parse.quote(student.email)
            base_frontend_url = (frontend_url or settings.FRONTEND_URL).rstrip("/")
            link = f"{base_frontend_url}/assessment/verify?token={existing_sa.token}&email={encoded_email}"
            
            return StudentAssessmentResponse(
                id=existing_sa.id,
                assessment_id=existing_sa.assessment_id,
                student_name=existing_sa.student_name,
                student_class=existing_sa.student_class,
                date_of_birth=existing_sa.date_of_birth,
                student_email=existing_sa.student_email,
                contact=existing_sa.contact,
                token=existing_sa.token,
                created_at=existing_sa.created_at,
                expires_at=existing_sa.expires_at,
                is_used=existing_sa.is_used,
                session_id=existing_sa.session_id,
                status=existing_sa.status,
                assessment_link=link,
                email_content=""
            )

        # 5. Create new StudentAssessment record
        from app.models.class_model import Class
        cls = self.db.query(Class).filter(Class.id == asmt.class_id).first()
        class_name = f"{cls.name} ({cls.section})" if cls else "Unknown Class"

        token = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow()
        expires_at = created_at + datetime.timedelta(hours=24)

        sa = StudentAssessment(
            assessment_id=asmt.id,
            student_name=student.name,
            student_class=class_name,
            date_of_birth="2010-01-01",  # Fallback DOB
            student_email=student.email,
            contact=student.contact_number or "0000000000",  # Fallback contact
            token=token,
            created_at=created_at,
            expires_at=expires_at,
            is_used=False,
            status="Pending",
            tenant_id=asmt.tenant_id
        )
        self.db.add(sa)
        self.db.commit()
        self.db.refresh(sa)

        # Generate link
        encoded_email = urllib.parse.quote(student.email)
        base_frontend_url = (frontend_url or settings.FRONTEND_URL).rstrip("/")
        link = f"{base_frontend_url}/assessment/verify?token={token}&email={encoded_email}"

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
            email_content=""
        )

