import unittest
import datetime
import json
from unittest.mock import patch
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.db.base import Base

from app.models.class_model import Class
from app.models.subject import Subject
from app.models.assessment import Assessment
from app.models.student_assessment import StudentAssessment
from app.models.interview import Interview

from app.services.interview_service import InterviewService
from app.schemas.interview_schema import InterviewSubmitRequest, TranscriptEntry

class TestInterviewService(unittest.TestCase):
    def setUp(self):
        # Reset DB tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        self.db = SessionLocal()

        # Seed necessary tables
        self.test_class = Class(name="Grade 1", grade="1", section="A")
        self.db.add(self.test_class)
        self.db.commit()

        self.subject = Subject(name="English", code="ENG1", status="Active", class_id=self.test_class.id)
        self.db.add(self.subject)
        self.db.commit()

        self.asmt = Assessment(
            title="Buddy Admissions Interview",
            subject_id=self.subject.id,
            class_id=self.test_class.id,
            status="Active",
            date="2026-05-29",
            questions_count=7
        )
        self.db.add(self.asmt)
        self.db.commit()

        self.sa = StudentAssessment(
            assessment_id=self.asmt.id,
            student_name="Charlie Brown",
            student_class="Grade 1A",
            date_of_birth="2020-09-15",
            student_email="charlie@example.com",
            contact="1234567890",
            token="token_valid",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            is_used=False,
            status="Pending"
        )
        self.db.add(self.sa)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_start_interview_success(self):
        """test_start_interview_success: verifies starting interview consumes token and creates database row."""
        service = InterviewService(self.db)
        
        result = service.start_interview("token_valid", "charlie@example.com")
        
        self.assertEqual(result["student_name"], "Charlie Brown")
        self.assertEqual(result["assessment_title"], "Buddy Admissions Interview")
        self.assertTrue(len(result["questions"]) > 0)
        
        # Verify student assessment token was consumed
        self.db.refresh(self.sa)
        self.assertTrue(self.sa.is_used)
        self.assertEqual(self.sa.status, "Started")
        
        # Verify interview row exists
        iv = self.db.query(Interview).filter(Interview.id == result["interview_id"]).first()
        self.assertIsNotNone(iv)
        self.assertEqual(iv.status, "In Progress")

    def test_start_interview_invalid_token(self):
        """test_start_interview_invalid_token: starting fails for invalid/expired tokens."""
        service = InterviewService(self.db)
        
        # 1. Non-existent token
        with self.assertRaises(ValueError) as ctx:
            service.start_interview("token_nonexistent", "charlie@example.com")
        self.assertIn("Invalid token", str(ctx.exception))
        
        # 2. Email mismatch
        with self.assertRaises(ValueError) as ctx:
            service.start_interview("token_valid", "wrong@example.com")
        self.assertIn("Email mismatch", str(ctx.exception))

        # 3. Already used token
        self.sa.is_used = True
        self.db.commit()
        with self.assertRaises(ValueError) as ctx:
            service.start_interview("token_valid", "charlie@example.com")
        self.assertIn("already been used", str(ctx.exception))

    @patch("app.services.interview_service.InterviewService._call_groq")
    def test_submit_and_analyse_flow(self, mock_call_groq):
        """test_submit_and_analyse_flow: submitting updates interview and student assessment status."""
        service = InterviewService(self.db)
        
        # Set up a started interview
        start_res = service.start_interview("token_valid", "charlie@example.com")
        interview_id = start_res["interview_id"]

        # Mock Groq API response
        mock_call_groq.return_value = {
            "overallScore": 85,
            "grade": "A",
            "summary": "Charlie spoke well and showed basic numeracy skills.",
            "skills": {
                "communication": 90,
                "numeracy": 80,
                "creativity": 85,
                "emotionalIntelligence": 85
            },
            "strengths": "Good communication skills and creativity.",
            "improvements": "Practice addition subtraction.",
            "recommendation": "Recommended",
            "adminNote": "Bright kid."
        }

        # Build payload
        payload = InterviewSubmitRequest(
            interview_id=interview_id,
            transcript=[
                TranscriptEntry(role="ai", text="Hello!", question_category="Introduction"),
                TranscriptEntry(role="student", text="My name is Charlie and I am 5.", question_category="Introduction")
            ],
            answers=[
                {"question_category": "Introduction", "question": "Hello!", "answer": "My name is Charlie and I am 5."}
            ]
        )

        # Submit
        iv = service.submit_and_analyse(payload)
        
        # Verify database fields updated
        self.assertEqual(iv.status, "Completed")
        self.assertEqual(iv.overall_score, 85)
        self.assertEqual(iv.grade, "A")
        self.assertEqual(iv.recommendation, "Recommended")
        self.assertEqual(iv.score_communication, 90)
        self.assertEqual(iv.score_numeracy, 80)
        
        # Verify student assessment is marked as completed
        self.db.refresh(self.sa)
        self.assertEqual(self.sa.status, "Completed")
        
        # Verify we can fetch the report
        report = service.get_report(interview_id)
        self.assertEqual(report.overall_score, 85)

if __name__ == "__main__":
    unittest.main()
