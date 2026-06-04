import unittest
import datetime
from unittest.mock import patch
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.db.base import Base

from app.models.class_model import Class
from app.models.subject import Subject
from app.models.chapter import Chapter
from app.models.question import Question
from app.models.assessment import Assessment
from app.models.report import Report
from app.models.student_assessment import StudentAssessment

from app.services.student_assessment_service import StudentAssessmentService
from app.services.assessment_service import AssessmentService
from app.schemas.student_assessment_schema import StudentAssessmentCreate, StudentAssessmentStartRequest
from app.schemas.assessment_schema import SubmitAnswersParams

class TestStudentAssessmentFlow(unittest.TestCase):
    def setUp(self):
        # Reset DB tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        self.db = SessionLocal()

        # Seed initial data
        self.test_class = Class(name="Grade 5", grade="5", section="A")
        self.db.add(self.test_class)
        self.db.commit()

        self.subject = Subject(name="Mathematics", code="MATH5", status="Active", class_id=self.test_class.id)
        self.db.add(self.subject)
        self.db.commit()

        self.chapter = Chapter(number="1", title="Addition", subject_id=self.subject.id)
        self.db.add(self.chapter)
        self.db.commit()

        # Seed a question
        self.question = Question(
            text="What is 10 + 20?",
            options=["10", "20", "30", "40"],
            correct_answer="30",
            difficulty="easy",
            cognitive_level="remembering",
            subject_id=self.subject.id,
            chapter_id=self.chapter.id
        )
        self.db.add(self.question)
        self.db.commit()

        # Seed base assessment
        self.asmt = Assessment(
            title="Addition Diagnostic",
            subject_id=self.subject.id,
            class_id=self.test_class.id,
            status="Active",
            date="2026-05-21",
            questions_count=1
        )
        self.db.add(self.asmt)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_assign_assessment(self):
        """Test assigning assessment creates token, expiration (24h), and simulated email."""
        service = StudentAssessmentService(self.db)
        
        create_schema = StudentAssessmentCreate(
            assessmentId=self.asmt.id,
            studentName="Alice Smith",
            studentClass="Grade 5A",
            dateOfBirth="2016-04-12",
            studentEmail="alice@example.com",
            contact="9876543210"
        )

        res = service.assign_assessment(create_schema)

        # Verify created DB record properties
        sa = self.db.query(StudentAssessment).filter(StudentAssessment.id == res.id).first()
        self.assertIsNotNone(sa)
        self.assertEqual(sa.student_name, "Alice Smith")
        self.assertEqual(sa.student_class, "Grade 5A")
        self.assertEqual(sa.date_of_birth, "2016-04-12")
        self.assertEqual(sa.student_email, "alice@example.com")
        self.assertEqual(sa.contact, "9876543210")
        self.assertFalse(sa.is_used)
        self.assertEqual(sa.status, "Pending")
        self.assertIsNotNone(sa.token)
        
        # Verify 24 hours expiration
        time_diff = sa.expires_at - sa.created_at
        self.assertAlmostEqual(time_diff.total_seconds(), 24 * 3600, delta=10)

        # Verify response link and simulated email content
        self.assertIn(sa.token, res.assessment_link)
        self.assertIn("alice%40example.com", res.assessment_link)
        self.assertIn("Alice Smith", res.email_content)
        self.assertIn("Addition Diagnostic", res.email_content)

    def test_verify_token_scenarios(self):
        """Test all verification scenarios (success, expired, used, email mismatch)."""
        service = StudentAssessmentService(self.db)
        
        # 1. Success case
        sa = StudentAssessment(
            assessment_id=self.asmt.id,
            student_name="Alice Smith",
            student_class="Grade 5A",
            date_of_birth="2016-04-12",
            student_email="alice@example.com",
            contact="9876543210",
            token="token_success",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            is_used=False,
            status="Pending"
        )
        self.db.add(sa)
        self.db.commit()

        verify_res = service.verify_token("token_success", "alice@example.com")
        self.assertTrue(verify_res.valid)
        self.assertEqual(verify_res.student_name, "Alice Smith")
        self.assertEqual(verify_res.student_email, "alice@example.com")
        self.assertEqual(verify_res.assessment_title, "Addition Diagnostic")

        # 2. Email mismatch case (case-insensitive checking should pass, but entirely different email fails)
        verify_case_insensitive = service.verify_token("token_success", " ALICE@example.com ")
        self.assertTrue(verify_case_insensitive.valid)

        verify_mismatch = service.verify_token("token_success", "wrong@example.com")
        self.assertFalse(verify_mismatch.valid)
        self.assertIn("Email mismatch", verify_mismatch.reason)

        # 3. Already used case
        sa.is_used = True
        self.db.commit()
        verify_used = service.verify_token("token_success", "alice@example.com")
        self.assertFalse(verify_used.valid)
        self.assertIn("already been used", verify_used.reason)

        # 4. Expired case
        sa.is_used = False
        sa.expires_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        self.db.commit()
        verify_expired = service.verify_token("token_success", "alice@example.com")
        self.assertFalse(verify_expired.valid)
        self.assertIn("expired", verify_expired.reason)
        
        # Checking if status in DB updated to Expired
        self.db.refresh(sa)
        self.assertEqual(sa.status, "Expired")

        # 5. Invalid token case
        verify_invalid = service.verify_token("non_existent_token", "alice@example.com")
        self.assertFalse(verify_invalid.valid)
        self.assertIn("Invalid token", verify_invalid.reason)

    def test_start_session_by_token(self):
        """Test starting assessment via token consumes link and sets status to Started."""
        service = StudentAssessmentService(self.db)
        
        sa = StudentAssessment(
            assessment_id=self.asmt.id,
            student_name="Alice Smith",
            student_class="Grade 5A",
            date_of_birth="2016-04-12",
            student_email="alice@example.com",
            contact="9876543210",
            token="token_start",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            is_used=False,
            status="Pending"
        )
        self.db.add(sa)
        self.db.commit()

        start_res = service.start_session_by_token("token_start", "alice@example.com")
        self.assertIsNotNone(start_res["sessionId"])
        self.assertEqual(start_res["assessment"]["title"], "Addition Diagnostic")
        self.assertEqual(len(start_res["assessment"]["questions"]), 1)
        
        # Verify db update
        self.db.refresh(sa)
        self.assertTrue(sa.is_used)
        self.assertEqual(sa.status, "Started")
        self.assertEqual(sa.session_id, start_res["sessionId"])

        # Try to start again - should fail
        with self.assertRaises(ValueError) as ctx:
            service.start_session_by_token("token_start", "alice@example.com")
        self.assertIn("already been used", str(ctx.exception))

    @patch("app.ai.gemini_provider.GeminiProvider.is_configured", return_value=False)
    def test_submit_session_answers_maps_student_details(self, mock_gemini_config):
        """Test submitting answers parses token session ID, completes status, and writes details to report."""
        sa_service = StudentAssessmentService(self.db)
        asmt_service = AssessmentService(self.db)

        sa = StudentAssessment(
            assessment_id=self.asmt.id,
            student_name="Alice Smith",
            student_class="Grade 5A",
            date_of_birth="2016-04-12",
            student_email="alice@example.com",
            contact="9876543210",
            token="token_submit",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            is_used=False,
            status="Pending"
        )
        self.db.add(sa)
        self.db.commit()

        # Start session
        start_res = sa_service.start_session_by_token("token_submit", "alice@example.com")
        session_id = start_res["sessionId"]

        # Submit answers
        submit_params = SubmitAnswersParams(
            session_id=session_id,
            answers={
                str(self.question.id): "30" # Correct answer
            }
        )
        submit_res = asmt_service.submit_session_answers(submit_params, self.db)
        
        self.assertEqual(submit_res.score, 100.0)

        # Verify StudentAssessment status is now Completed
        self.db.refresh(sa)
        self.assertEqual(sa.status, "Completed")

        # Verify Report metadata contains student information
        report_id = int(submit_res.result_id.split("_")[1])
        report = self.db.query(Report).filter(Report.id == report_id).first()
        
        self.assertIsNotNone(report)
        self.assertEqual(report.student_name, "Alice Smith")
        self.assertEqual(report.student_email, "alice@example.com")
        self.assertEqual(report.student_class, "Grade 5A")
        self.assertEqual(report.date_of_birth, "2016-04-12")
        self.assertEqual(report.contact, "9876543210")

if __name__ == "__main__":
    unittest.main()
