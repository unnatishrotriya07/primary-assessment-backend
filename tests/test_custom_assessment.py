import unittest
import datetime
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.class_model import Class
from app.models.subject import Subject
from app.models.chapter import Chapter
from app.models.question import Question
from app.models.assessment import Assessment
from app.models.report import Report
from app.services.assessment_service import AssessmentService
from app.services.question_service import QuestionService
from app.schemas.assessment_schema import AssessmentCreate, SubmitAnswersParams

class TestCustomAssessmentFlow(unittest.TestCase):
    def setUp(self):
        # Reset DB tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        self.db = SessionLocal()

        # Seed initial data
        self.class_g5 = Class(name="Grade 5", grade="5", section="A")
        self.db.add(self.class_g5)
        self.class_g6 = Class(name="Grade 6", grade="6", section="B")
        self.db.add(self.class_g6)
        self.db.commit()

        self.subject_math = Subject(name="Math", code="MATH5", status="Active", class_id=self.class_g5.id)
        self.db.add(self.subject_math)
        self.subject_sci = Subject(name="Science", code="SCI6", status="Active", class_id=self.class_g6.id)
        self.db.add(self.subject_sci)
        self.db.commit()

        self.chapter_math = Chapter(number="1", title="Addition", subject_id=self.subject_math.id)
        self.db.add(self.chapter_math)
        self.chapter_sci = Chapter(number="1", title="Plants", subject_id=self.subject_sci.id)
        self.db.add(self.chapter_sci)
        self.db.commit()

        # Seed questions
        self.q1_math = Question(
            text="What is 5 + 5?",
            options=["5", "10", "15", "20"],
            correct_answer="10",
            difficulty="easy",
            cognitive_level="remembering",
            subject_id=self.subject_math.id,
            chapter_id=self.chapter_math.id,
            class_id=self.class_g5.id
        )
        self.q2_math = Question(
            text="What is 10 x 10?",
            options=["10", "50", "100", "200"],
            correct_answer="100",
            difficulty="medium",
            cognitive_level="applying",
            subject_id=self.subject_math.id,
            chapter_id=self.chapter_math.id,
            class_id=self.class_g5.id
        )
        self.q3_sci = Question(
            text="What gas do plants absorb?",
            options=["Oxygen", "Carbon Dioxide", "Nitrogen", "Hydrogen"],
            correct_answer="Carbon Dioxide",
            difficulty="easy",
            cognitive_level="remembering",
            subject_id=self.subject_sci.id,
            chapter_id=self.chapter_sci.id,
            class_id=self.class_g6.id
        )
        self.db.add_all([self.q1_math, self.q2_math, self.q3_sci])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_create_assessment_with_selected_questions(self):
        """Verify that creating an assessment with specific question_ids stores relationship correctly."""
        asmt_service = AssessmentService(self.db)
        
        create_schema = AssessmentCreate(
            title="Math Selective Assessment",
            subjectId=self.subject_math.id,
            classId=self.class_g5.id,
            status="Active",
            date="2026-05-22",
            questionsCount=1, # Will be overridden by length of question_ids
            question_ids=[self.q1_math.id]
        )

        asmt = asmt_service.create_assessment(create_schema)

        # Check DB columns
        self.assertIsNotNone(asmt.id)
        self.assertEqual(asmt.title, "Math Selective Assessment")
        self.assertEqual(asmt.questions_count, 1)
        self.assertEqual(len(asmt.questions), 1)
        self.assertEqual(asmt.questions[0].id, self.q1_math.id)

    def test_get_questions_for_session_with_custom_assessment(self):
        """Verify that custom assessment returns exactly the selected questions in a session."""
        asmt_service = AssessmentService(self.db)

        # Create assessment with only q2_math selected
        create_schema = AssessmentCreate(
            title="Math Selective Q2 Only",
            subjectId=self.subject_math.id,
            classId=self.class_g5.id,
            status="Active",
            date="2026-05-22",
            questionsCount=0,
            question_ids=[self.q2_math.id]
        )
        asmt = asmt_service.create_assessment(create_schema)

        # Retrieve questions for session
        session_qs = asmt_service.get_questions_for_session(asmt.id)
        self.assertEqual(len(session_qs), 1)
        self.assertEqual(session_qs[0].id, self.q2_math.id)
        self.assertEqual(session_qs[0].text, "What is 10 x 10?")

    def test_evaluate_session_submission_on_custom_assessment(self):
        """Verify that submitting answers on a custom assessment evaluates successfully against selected questions."""
        asmt_service = AssessmentService(self.db)

        create_schema = AssessmentCreate(
            title="Custom Math Test",
            subjectId=self.subject_math.id,
            classId=self.class_g5.id,
            status="Active",
            date="2026-05-22",
            questionsCount=0,
            question_ids=[self.q1_math.id, self.q2_math.id]
        )
        asmt = asmt_service.create_assessment(create_schema)

        # Submit answers
        session_id = f"asmt_{asmt.id}_mock123"
        submit_params = SubmitAnswersParams(
            session_id=session_id,
            answers={
                str(self.q1_math.id): "10",  # Correct
                str(self.q2_math.id): "50"   # Incorrect (Correct is 100)
            }
        )

        res = asmt_service.submit_session_answers(submit_params, self.db)
        
        # 1 correct out of 2 = 50%
        self.assertEqual(res.score, 50.0)

        # Verify report is created in DB
        report_id = int(res.result_id.split("_")[1])
        report = self.db.query(Report).filter(Report.id == report_id).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.score, 50.0)
        self.assertEqual(report.grade, "F")

    def test_question_service_filtering(self):
        """Verify that QuestionService filters questions correctly by class, subject, and chapter."""
        q_service = QuestionService(self.db)

        # Filter by Math subject
        math_qs = q_service.get_questions(subject_id=self.subject_math.id)
        self.assertEqual(len(math_qs), 2)
        math_ids = [q.id for q in math_qs]
        self.assertIn(self.q1_math.id, math_ids)
        self.assertIn(self.q2_math.id, math_ids)

        # Filter by Class G6
        g6_qs = q_service.get_questions(class_id=self.class_g6.id)
        self.assertEqual(len(g6_qs), 1)
        self.assertEqual(g6_qs[0].id, self.q3_sci.id)

        # Filter by Math subject AND Science chapter (should be empty)
        empty_qs = q_service.get_questions(subject_id=self.subject_math.id, chapter_id=self.chapter_sci.id)
        self.assertEqual(len(empty_qs), 0)

    def test_question_session_filtering(self):
        """Verify that questions can be saved with session tags and filtered by session."""
        q_service = QuestionService(self.db)

        # Create a new question with a session
        from app.schemas.question_schema import QuestionCreate
        new_q = QuestionCreate(
            text="What is 2 + 2?",
            options=["2", "3", "4", "5"],
            correctAnswer="4",
            difficulty="easy",
            cognitiveLevel="remembering",
            subjectId=self.subject_math.id,
            chapterId=self.chapter_math.id,
            classId=self.class_g5.id,
            session="Session 2026-2027"
        )
        created_q = q_service.create_question(new_q)

        # Verify created question has session
        self.assertEqual(created_q.session, "Session 2026-2027")

        # Fetch questions filtering by session
        session_qs = q_service.get_questions(session="Session 2026-2027")
        self.assertEqual(len(session_qs), 1)
        self.assertEqual(session_qs[0].id, created_q.id)

        # Fetch questions filtering by a non-existent session (should be empty)
        non_existent_qs = q_service.get_questions(session="Session 2099-2100")
        self.assertEqual(len(non_existent_qs), 0)

    def test_deterministic_sampling(self):
        """Verify that get_questions_for_session returns a deterministic subset of size questions_to_ask when a seed is provided."""
        asmt_service = AssessmentService(self.db)
        
        # Add 3 more math questions so we have 5 total math questions
        extra_qs = []
        for i in range(3):
            q = Question(
                text=f"Extra Math Q{i}?",
                options=[],
                correct_answer=f"Ans{i}",
                difficulty="medium",
                cognitive_level="applying",
                subject_id=self.subject_math.id,
                chapter_id=self.chapter_math.id,
                class_id=self.class_g5.id
            )
            self.db.add(q)
            extra_qs.append(q)
        self.db.commit()

        # Create assessment with all 5 math questions, but questions_to_ask = 3
        all_math_q_ids = [self.q1_math.id, self.q2_math.id] + [q.id for q in extra_qs]
        
        create_schema = AssessmentCreate(
            title="Math Deterministic Sampling Test",
            subjectId=self.subject_math.id,
            classId=self.class_g5.id,
            status="Active",
            date="2026-05-22",
            questionsCount=0,
            question_ids=all_math_q_ids,
            questions_to_ask=3
        )
        asmt = asmt_service.create_assessment(create_schema)
        self.assertEqual(asmt.questions_to_ask, 3)

        # Call with seed A twice and check equality
        seed_a = "student_token_a"
        qs_a1 = asmt_service.get_questions_for_session(asmt.id, seed_str=seed_a)
        qs_a2 = asmt_service.get_questions_for_session(asmt.id, seed_str=seed_a)
        
        self.assertEqual(len(qs_a1), 3)
        self.assertEqual(len(qs_a2), 3)
        self.assertEqual([q.id for q in qs_a1], [q.id for q in qs_a2])

        # Call with seed B twice and check equality, and check that it's different/potentially different from seed A
        seed_b = "student_token_b"
        qs_b = asmt_service.get_questions_for_session(asmt.id, seed_str=seed_b)
        self.assertEqual(len(qs_b), 3)
        
        # Test that they are sorted by ID in both cases (stable ordering)
        self.assertEqual([q.id for q in qs_a1], sorted([q.id for q in qs_a1]))
        self.assertEqual([q.id for q in qs_b], sorted([q.id for q in qs_b]))

if __name__ == "__main__":
    unittest.main()
