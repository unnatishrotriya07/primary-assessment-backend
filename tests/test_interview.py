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

    @patch("app.services.interview_service.InterviewService._call_groq")
    def test_submit_and_analyse_background_flow(self, mock_call_groq):
        """test_submit_and_analyse_background_flow: background evaluation sets status correctly."""
        service = InterviewService(self.db)
        
        # Set up a started interview
        start_res = service.start_interview("token_valid", "charlie@example.com")
        interview_id = start_res["interview_id"]

        # Mock Groq API response
        mock_call_groq.return_value = {
            "overallScore": 95,
            "grade": "A+",
            "summary": "Excellent evaluation.",
            "skills": {
                "communication": 95,
                "numeracy": 95,
                "creativity": 95,
                "emotionalIntelligence": 95
            },
            "strengths": "Everything.",
            "improvements": "None.",
            "recommendation": "Strongly Recommended",
            "adminNote": "Superb."
        }

        # Build payload
        payload = InterviewSubmitRequest(
            interview_id=interview_id,
            transcript=[
                TranscriptEntry(role="ai", text="Hello!", question_category="Introduction"),
                TranscriptEntry(role="student", text="Hi.", question_category="Introduction")
            ],
            answers=[
                {"question_category": "Introduction", "question": "Hello!", "answer": "Hi."}
            ]
        )

        # 1. Step 1: Set status to Transcript Saved and save transcript
        iv = service.save_submission_and_set_evaluating(payload)
        self.assertEqual(iv.status, "Transcript Saved")

        # 2. Step 2: Prepare context
        context = service.prepare_eval_context(iv, payload.answers)
        self.assertEqual(len(context), 1)

        # 3. Step 3: Run the background job (V2 pipeline)
        service.evaluate_interview_in_background_v2(interview_id)

        # 4. Verify DB fields updated after background execution
        self.db.refresh(iv)
        self.assertEqual(iv.status, "Report Ready")
        self.assertTrue(iv.overall_score >= 0)

    def test_update_notes(self):
        """test_update_notes: verifies update_notes updates interview admin_note correctly."""
        service = InterviewService(self.db)
        
        # 1. Initialize interview row
        iv = Interview(
            student_assessment_id=self.sa.id,
            assessment_id=self.asmt.id,
            student_name="Charlie Brown",
            student_class="Grade 1A",
            status="In Progress"
        )
        self.db.add(iv)
        self.db.commit()

        # 2. Call update_notes
        updated_report = service.update_notes(iv.id, "Teacher remark notes here.")
        
        # 3. Assert value is set
        self.assertEqual(updated_report.admin_note, "Teacher remark notes here.")
        
        # 4. Assert DB state is persisted
        self.db.refresh(iv)
        self.assertEqual(iv.admin_note, "Teacher remark notes here.")

    def test_add_message_success(self):
        """test_add_message_success: verifies adding a message records turn details and updates sequence/confidence."""
        service = InterviewService(self.db)
        start_res = service.start_interview("token_valid", "charlie@example.com")
        interview_id = start_res["interview_id"]

        # Add message
        msg = service.add_message(
            interview_id=interview_id,
            role="student",
            text="I think the answer is 1/2.",
            question_category="Fractions",
            sequence_number=1,
            speech_confidence=0.88
        )
        self.assertEqual(msg.role, "student")
        self.assertEqual(msg.text, "I think the answer is 1/2.")
        self.assertEqual(msg.speech_confidence, 0.88)
        self.assertEqual(msg.sequence_number, 1)

    def test_update_session_state(self):
        """test_update_session_state: verifies progressive updates of current index, comfort state, answers."""
        service = InterviewService(self.db)
        start_res = service.start_interview("token_valid", "charlie@example.com")
        interview_id = start_res["interview_id"]

        raw_answers = [{"question_category": "Fractions", "question": "What is half of 4?", "answer": "2"}]
        iv = service.update_session_state(
            interview_id=interview_id,
            current_question_index=3,
            session_state="interview",
            comfort_index=2,
            raw_answers=raw_answers,
            network_status="online",
            completion_status="In Progress"
        )
        self.assertEqual(iv.current_question_index, 3)
        self.assertEqual(iv.session_state, "interview")
        self.assertEqual(iv.comfort_index, 2)
        self.assertEqual(iv.raw_answers, raw_answers)
        self.assertEqual(iv.network_status, "online")

    @patch("app.services.evaluation_pipeline.EvaluationPipelineService._call_llm_with_fallback")
    def test_evaluation_pipeline_with_review_flags(self, mock_llm_call):
        """test_evaluation_pipeline_with_review_flags: pipeline flags low confidence evaluations/transcripts."""
        from app.services.evaluation_pipeline import EvaluationPipelineService
        service = InterviewService(self.db)
        start_res = service.start_interview("token_valid", "charlie@example.com")
        interview_id = start_res["interview_id"]

        # Save student message with low speech confidence (< 0.70)
        service.add_message(
            interview_id=interview_id,
            role="student",
            text="mumble half...",
            question_category="Fractions",
            sequence_number=1,
            speech_confidence=0.55
        )

        # Mock low evaluation confidence for questions
        mock_llm_call.side_effect = [
            # Cleanup output
            {"dialogue": [{"role": "student", "text": "mumble half...", "category": "Fractions"}]},
            # Question mapping
            [{"index": 1, "question": "What is half of 4?", "student_answer": "mumble half...", "expected_answer": "2", "options": [], "question_type": "tita"}],
            # Answer understanding
            [{"index": 1, "question": "What is half of 4?", "student_answer": "mumble half...", "is_skipped": False, "is_partial": True, "has_speech_issue": True, "cleaned_response": "mumble half"}],
            # Per-question evaluation (returns low evaluation confidence - Attempt 1)
            {"concept": "Fractions", "masteryScore": 40, "confidence": 50, "reasoning": "Unclear student answer", "misconception": "Speech issue", "evidence": "mumble"},
            # Per-question evaluation retry (Attempt 2)
            {"concept": "Fractions", "masteryScore": 40, "confidence": 50, "reasoning": "Unclear student answer", "misconception": "Speech issue", "evidence": "mumble"},
            # Concept mastery
            {"subjectMastery": 40, "chapterMastery": 40, "concepts": [], "bloomDistribution": {}},
            # Learning gaps
            {"gaps": []},
            # Strengths
            {"strengths": []},
            # Recommendations
            {"recommendations": []},
            # Teacher summary
            {"summary": "Needs review"},
            # Parent summary
            {"parent_summary": "Encouraging letter"}
        ]

        pipeline = EvaluationPipelineService(self.db)
        result = pipeline.run_pipeline(interview_id)

        self.assertEqual(result["status"], "Report Ready")
        self.assertTrue(result["requires_review"])

        # Fetch db record and assert review flags
        iv = self.db.query(Interview).filter(Interview.id == interview_id).first()
        self.assertTrue(iv.requires_review)
        self.assertIn("Low speech recognition confidence", iv.review_reason)

    def test_review_and_approve_report(self):
        """test_review_and_approve_report: teacher review overrides score and clears requires_review status."""
        service = InterviewService(self.db)
        
        # Create a report requiring review
        iv = Interview(
            student_assessment_id=self.sa.id,
            assessment_id=self.asmt.id,
            student_name="Charlie Brown",
            student_class="Grade 1A",
            status="Report Ready",
            requires_review=True,
            review_reason="Low speech confidence",
            evaluated_answers=[
                {"question": "What is half of 4?", "studentAnswer": "mumble", "expectedAnswer": "2", "isCorrect": False, "masteryScore": 0, "confidence": 50}
            ]
        )
        self.db.add(iv)
        self.db.commit()

        # Approve review and correct the grading to True / score 100
        corrected_answers = [
            {"question": "What is half of 4?", "studentAnswer": "mumble", "expectedAnswer": "2", "isCorrect": True, "masteryScore": 100, "confidence": 100}
        ]
        
        updated_iv = service.review_and_approve_report(
            interview_id=iv.id,
            evaluated_answers=corrected_answers,
            admin_note="Corrected manual grading."
        )

        self.assertFalse(updated_iv.requires_review)
        self.assertIsNone(updated_iv.review_reason)
        self.assertEqual(updated_iv.overall_score, 100.0)
        self.assertEqual(updated_iv.grade, "A+")
        self.assertEqual(updated_iv.admin_note, "Corrected manual grading.")

if __name__ == "__main__":
    unittest.main()

