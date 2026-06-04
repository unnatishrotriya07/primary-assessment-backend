import unittest
from unittest.mock import MagicMock, patch
import json

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.base import Base

from app.models.class_model import Class
from app.models.subject import Subject
from app.models.chapter import Chapter
from app.models.question import Question
from app.models.assessment import Assessment
from app.models.report import Report

from app.ai.gemini_provider import GeminiProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.groq_provider import GroqProvider
from app.ai.answer_evaluator import AnswerEvaluator
from app.ai.report_generator import ReportGenerator
from app.services.assessment_service import AssessmentService
from app.schemas.assessment_schema import SubmitAnswersParams

class TestHybridAIAchitecture(unittest.TestCase):
    
    def setUp(self):
        # Drop and create tables to start fresh
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        self.db = SessionLocal()
        
        # Setup mock entities
        self.test_class = Class(name="Test Class 5", grade="5", section="A")
        self.db.add(self.test_class)
        self.db.commit()
        
        self.math_sub = Subject(name="Test Mathematics", code="MATH_TEST", status="Active", class_id=self.test_class.id)
        self.db.add(self.math_sub)
        self.db.commit()
        
        self.math_ch = Chapter(number="1", title="Test Math Basics", subject_id=self.math_sub.id)
        self.db.add(self.math_ch)
        self.db.commit()
        
        # Seed questions
        # Q1: Objective MCQ
        self.q_mcq = Question(
            text="What is 5 + 7?",
            options=["10", "11", "12", "13"],
            correct_answer="12",
            difficulty="easy",
            cognitive_level="remembering",
            subject_id=self.math_sub.id,
            chapter_id=self.math_ch.id
        )
        # Q2: Numerical / Math
        self.q_math = Question(
            text="Solve for x: x - 4 = 10",
            options=[],
            correct_answer="14",
            difficulty="easy",
            cognitive_level="applying",
            subject_id=self.math_sub.id,
            chapter_id=self.math_ch.id
        )
        
        self.science_sub = Subject(name="Test Science", code="SCI_TEST", status="Active", class_id=self.test_class.id)
        self.db.add(self.science_sub)
        self.db.commit()
        
        self.science_ch = Chapter(number="2", title="Test Photosynthesis", subject_id=self.science_sub.id)
        self.db.add(self.science_ch)
        self.db.commit()

        # Q3: Descriptive Science Question
        self.q_desc = Question(
            text="Explain why plants are green.",
            options=[],
            correct_answer="Plants are green because they contain chlorophyll, which absorbs blue and red light.",
            difficulty="medium",
            cognitive_level="understanding",
            subject_id=self.science_sub.id,
            chapter_id=self.science_ch.id
        )
        
        self.db.add(self.q_mcq)
        self.db.add(self.q_math)
        self.db.add(self.q_desc)
        self.db.commit()
        
        # Setup assessment
        self.asmt = Assessment(
            id=1,
            title="Science & Math Diagnostic",
            subject_id=self.math_sub.id,
            class_id=self.test_class.id,
            status="Active",
            date="2026-05-21",
            questions_count=2
        )
        self.db.add(self.asmt)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        
    def test_provider_signatures(self):
        """Verify all providers follow standard method signatures."""
        providers = [GeminiProvider, OpenAIProvider, GroqProvider]
        for provider_cls in providers:
            # Check generate method signature structure
            self.assertTrue(hasattr(provider_cls, "generate"))
            self.assertTrue(hasattr(provider_cls, "is_configured"))

    def test_answer_evaluator_rule_based(self):
        """Verify rule-based evaluation (case-insensitivity, float comparison)."""
        evaluator = AnswerEvaluator()
        
        # Test MCQ Question - Exact Match
        res = evaluator.evaluate(self.q_mcq, "12")
        self.assertTrue(res["is_correct"])
        self.assertEqual(res["evaluator"], "rule-based")
        
        # Test MCQ Question - Case Insensitivity (if text options)
        self.q_mcq.correct_answer = "Absorb sunlight"
        res = evaluator.evaluate(self.q_mcq, "absorb sunlight")
        self.assertTrue(res["is_correct"])
        
        # Test Numeric Question - Exact and Float Match
        self.q_math.correct_answer = "14"
        res = evaluator.evaluate(self.q_math, "14")
        self.assertTrue(res["is_correct"])
        
        res = evaluator.evaluate(self.q_math, "14.0")
        self.assertTrue(res["is_correct"])
        
        res = evaluator.evaluate(self.q_math, "14.00")
        self.assertTrue(res["is_correct"])
        
        res = evaluator.evaluate(self.q_math, "13")
        self.assertFalse(res["is_correct"])

    @patch("app.ai.gemini_provider.GeminiProvider.is_configured", return_value=True)
    @patch("app.ai.gemini_provider.GeminiProvider.generate")
    def test_answer_evaluator_descriptive_gemini(self, mock_generate, mock_configured):
        """Verify descriptive answers trigger Gemini evaluation and parse JSON correctly."""
        # Set up mock Gemini response
        mock_generate.return_value = '{"is_correct": true, "explanation": "Excellent and accurate explanation of chlorophyll."}'
        
        evaluator = AnswerEvaluator()
        res = evaluator.evaluate(self.q_desc, "Plants have chlorophyll which makes them green.")
        
        # Asserts
        self.assertTrue(res["is_correct"])
        self.assertEqual(res["evaluator"], "gemini")
        self.assertIn("chlorophyll", res["explanation"])
        mock_generate.assert_called_once()

    @patch("app.ai.gemini_provider.GeminiProvider.is_configured", return_value=True)
    @patch("app.ai.gemini_provider.GeminiProvider.generate")
    def test_report_generator_gemini_feedback(self, mock_generate, mock_configured):
        """Verify Gemini-based personalized report card feedback generation."""
        mock_generate.return_value = "Great job! The student has shown excellent proficiency in math concepts. Review photosynthesis equations to improve further."
        
        rep_gen = ReportGenerator()
        feedback = rep_gen.generate_report_feedback(
            score=90.0,
            accuracy=90.0,
            class_name="Test Class 5",
            subject_name="Test Mathematics",
            student_name="Test Student"
        )
        
        self.assertEqual(feedback, "Great job! The student has shown excellent proficiency in math concepts. Review photosynthesis equations to improve further.")
        mock_generate.assert_called_once()

    def test_report_generator_fallback(self):
        """Verify fallback report feedback is correct when Gemini is not configured."""
        # Force is_configured to return False
        with patch("app.ai.gemini_provider.GeminiProvider.is_configured", return_value=False):
            rep_gen = ReportGenerator()
            
            # High score
            feedback_high = rep_gen.generate_report_feedback(85.0, 85.0, "Test Class 5", "Test Mathematics", "Test Student")
            self.assertIn("Excellent performance in Test Mathematics", feedback_high)
            
            # Mid score
            feedback_mid = rep_gen.generate_report_feedback(70.0, 70.0, "Test Class 5", "Test Mathematics", "Test Student")
            self.assertIn("Good effort in Test Mathematics", feedback_mid)
            
            # Low score
            feedback_low = rep_gen.generate_report_feedback(40.0, 40.0, "Test Class 5", "Test Mathematics", "Test Student")
            self.assertIn("Pedagogical review recommended", feedback_low)

    @patch("app.ai.gemini_provider.GeminiProvider.is_configured", return_value=True)
    @patch("app.ai.gemini_provider.GeminiProvider.generate")
    def test_assessment_service_submission(self, mock_generate, mock_configured):
        """Verify full submit_session_answers pipeline compiles scores, evaluates answers, creates report, and stores feedback."""
        # Mock Gemini feedback response
        mock_generate.return_value = "Personalized AI Advice: Superb mathematical ability shown."
        
        service = AssessmentService(self.db)
        
        # Submitting answers for MCQ and Math questions
        params = SubmitAnswersParams(
            session_id="asmt_1_sessionuuid",
            answers={
                str(self.q_mcq.id): "12",       # Correct
                str(self.q_math.id): "14.0"      # Correct (float match)
            }
        )
        
        res = service.submit_session_answers(params, self.db)
        
        # Asserts
        self.assertEqual(res.score, 100.0)
        self.assertTrue(res.result_id.startswith("rep_"))
        
        # Retrieve generated report from DB
        report_id = int(res.result_id.split("_")[1])
        report = self.db.query(Report).filter(Report.id == report_id).first()
        
        self.assertIsNotNone(report)
        self.assertEqual(report.score, 100.0)
        self.assertEqual(report.grade, "A")
        self.assertEqual(report.feedback, "Personalized AI Advice: Superb mathematical ability shown.")
        
        # Verify assessment status is updated to Completed
        asmt_db = self.db.query(Assessment).filter(Assessment.id == 1).first()
        self.assertEqual(asmt_db.status, "Completed")

    @patch("app.ai.groq_provider.GroqProvider.is_configured", return_value=True)
    @patch("app.ai.groq_provider.GroqProvider.generate")
    def test_ai_generation_preview_only(self, mock_generate, mock_configured):
        """Verify that preview_only=True generates draft questions without writing them to the database."""
        mock_generate.return_value = '{"questions": [{"text": "Sample Preview Question?", "options": ["A", "B", "C", "D"], "correct_answer": "A"}]}'
        
        from app.schemas.question_schema import AIQuestionParams
        from app.services.question_service import QuestionService
        
        service = QuestionService(self.db)
        params = AIQuestionParams(
            class_id=self.test_class.id,
            subject_id=self.math_sub.id,
            chapter_id=self.math_ch.id,
            difficulty="easy",
            cognitive_level="remembering",
            count=1,
            regenerate=True,
            preview_only=True
        )
        
        # Track initial question count in DB
        initial_count = self.db.query(Question).count()
        
        # Generate with preview_only
        drafts = service.generate_ai_questions(params)
        
        # Check drafts return structure
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].text, "Sample Preview Question?")
        self.assertEqual(drafts[0].id, 0) # Unsaved ID indicator
        
        # Check DB count remains unchanged
        after_count = self.db.query(Question).count()
        self.assertEqual(initial_count, after_count)

    def test_batch_create_questions(self):
        """Verify batch_create_questions saves all drafts, and clear_existing deletes old matching questions."""
        from app.schemas.question_schema import QuestionCreate, QuestionBatchSave
        from app.services.question_service import QuestionService
        
        service = QuestionService(self.db)
        
        # 1. Create a batch of new questions
        q1 = QuestionCreate(
            text="New Batch Q1",
            options=["A", "B", "C", "D"],
            correct_answer="A",
            difficulty="medium",
            cognitive_level="applying",
            class_id=self.test_class.id,
            subject_id=self.math_sub.id,
            chapter_id=self.math_ch.id
        )
        q2 = QuestionCreate(
            text="New Batch Q2",
            options=[],
            correct_answer="42",
            difficulty="medium",
            cognitive_level="applying",
            class_id=self.test_class.id,
            subject_id=self.math_sub.id,
            chapter_id=self.math_ch.id
        )
        
        batch_in = QuestionBatchSave(
            questions=[q1, q2],
            clear_existing=False
        )
        
        saved = service.batch_create_questions(batch_in)
        
        # Check that we returned 2 saved items with positive database IDs
        self.assertEqual(len(saved), 2)
        self.assertGreater(saved[0].id, 0)
        self.assertGreater(saved[1].id, 0)
        
        # Verify persistence in DB
        db_q1 = self.db.query(Question).filter(Question.text == "New Batch Q1").first()
        db_q2 = self.db.query(Question).filter(Question.text == "New Batch Q2").first()
        self.assertIsNotNone(db_q1)
        self.assertIsNotNone(db_q2)
        self.assertEqual(db_q1.correct_answer, "A")
        self.assertEqual(db_q2.correct_answer, "42")
        
        # 2. Test clear_existing = True
        q3 = QuestionCreate(
            text="Replacing Batch Q3",
            options=[],
            correct_answer="Correct Answer",
            difficulty="medium",
            cognitive_level="applying",
            class_id=self.test_class.id,
            subject_id=self.math_sub.id,
            chapter_id=self.math_ch.id
        )
        
        replace_batch = QuestionBatchSave(
            questions=[q3],
            clear_existing=True,
            chapter_id=self.math_ch.id,
            difficulty="medium",
            cognitive_level="applying"
        )
        
        replaced_saved = service.batch_create_questions(replace_batch)
        
        self.assertEqual(len(replaced_saved), 1)
        self.assertEqual(replaced_saved[0].text, "Replacing Batch Q3")
        
        # Confirm that q1 and q2 (which were medium, applying in that chapter) were deleted
        deleted_q1 = self.db.query(Question).filter(Question.text == "New Batch Q1").first()
        deleted_q2 = self.db.query(Question).filter(Question.text == "New Batch Q2").first()
        self.assertIsNone(deleted_q1)
        self.assertIsNone(deleted_q2)
        
        # Confirm q3 exists
        inserted_q3 = self.db.query(Question).filter(Question.text == "Replacing Batch Q3").first()
        self.assertIsNotNone(inserted_q3)

if __name__ == "__main__":
    unittest.main()
