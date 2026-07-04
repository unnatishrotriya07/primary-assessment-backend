from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.class_model import Class
from app.models.subject import Subject
from app.models.chapter import Chapter
from app.models.question import Question
from app.schemas.question_schema import AIQuestionParams
from app.services.question_service import QuestionService

from unittest.mock import patch

@patch("app.ai.groq_provider.GroqProvider.is_configured", return_value=False)
@patch("app.ai.gemini_provider.GeminiProvider.is_configured", return_value=False)
@patch("app.ai.openai_provider.OpenAIProvider.is_configured", return_value=False)
def test_ai_generation_pipeline(mock_openai, mock_gemini, mock_groq):
    # Make sure all tables exist cleanly by dropping and recreating them
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Setup Test Data
        # Setup Class
        test_class = Class(name="Test Class 5", grade="5", section="A")
        db.add(test_class)
        db.commit()
        db.refresh(test_class)
            
        # Setup Math Subject & Chapter
        math_sub = Subject(name="Test Mathematics", code="MATH_TEST", status="Active", class_id=test_class.id)
        db.add(math_sub)
        db.commit()
        db.refresh(math_sub)
            
        math_ch = Chapter(number="1", title="Test Math Basics", subject_id=math_sub.id)
        db.add(math_ch)
        db.commit()
        db.refresh(math_ch)

        # Setup Science Subject & Chapter
        sci_sub = Subject(name="Test Science", code="SCI_TEST", status="Active", class_id=test_class.id)
        db.add(sci_sub)
        db.commit()
        db.refresh(sci_sub)
            
        sci_ch = Chapter(
            number="1",
            title="Test Photosynthesis",
            subject_id=sci_sub.id,
            content="Photosynthesis is the process by which green plants make food using carbon dioxide and water in the presence of sunlight."
        )
        db.add(sci_ch)
        db.commit()
        db.refresh(sci_ch)

        # Ensure database is clean of old test questions for these chapters
        db.query(Question).filter(Question.chapter_id.in_([math_ch.id, sci_ch.id])).delete(synchronize_session=False)
        db.commit()

        # Instantiate Question Service
        service = QuestionService(db)

        # 2. Test Math Generation (uses Template Generator)
        math_params = AIQuestionParams(
            class_id=test_class.id,
            subject_id=math_sub.id,
            chapter_id=math_ch.id,
            difficulty="easy",
            cognitive_level="remembering",
            count=3,
            regenerate=False
        )

        print("\n--- Generating Math Questions (Mock Fallback) ---")
        math_questions = service.generate_ai_questions(math_params)
        assert len(math_questions) == 3, f"Expected 3 questions, got {len(math_questions)}"
        
        for q in math_questions:
            assert q.generated_by == "mock", f"Expected generated_by to be 'mock', got {q.generated_by}"
            assert q.class_id == test_class.id
            assert q.subject_id == math_sub.id
            assert q.chapter_id == math_ch.id
            if q.question_type == "mcq":
                assert len(q.options) == 4
                assert q.correct_answer in q.options
            else:
                assert len(q.options) == 0
                assert q.correct_answer is not None
            print(f"Generated Question: {q.text} (Options: {q.options}, Correct: {q.correct_answer})")

        math_ids = [q.id for q in math_questions]

        # 3. Test Math Caching
        print("\n--- Testing Math Caching ---")
        cached_questions = service.generate_ai_questions(math_params)
        cached_ids = [q.id for q in cached_questions]
        assert math_ids == cached_ids, "Expected cached questions to have the same database IDs"
        print("Caching verification successful (same IDs returned).")

        # 4. Test Math Regeneration
        print("\n--- Testing Math Regeneration ---")
        math_params.regenerate = True
        regen_questions = service.generate_ai_questions(math_params)
        
        # Verify that the old questions were deleted by checking the total count in DB (should be 3, not 6)
        db_count = db.query(Question).filter(Question.chapter_id == math_ch.id).count()
        assert db_count == 3, f"Expected 3 questions in DB after regeneration, found {db_count}"
        assert len(regen_questions) == 3
        print("Regeneration verification successful (old questions deleted, new ones created).")

        # 5. Test Science Generation (falls back to Mock since API keys are empty/unset)
        sci_params = AIQuestionParams(
            class_id=test_class.id,
            subject_id=sci_sub.id,
            chapter_id=sci_ch.id,
            difficulty="medium",
            cognitive_level="understanding",
            count=2,
            regenerate=False
        )

        print("\n--- Generating Science Questions (Mock Fallback) ---")
        sci_questions = service.generate_ai_questions(sci_params)
        assert len(sci_questions) == 2, f"Expected 2 questions, got {len(sci_questions)}"
        
        for q in sci_questions:
            assert q.generated_by == "mock", f"Expected generated_by to be 'mock', got {q.generated_by}"
            assert q.class_id == test_class.id
            assert q.subject_id == sci_sub.id
            assert q.chapter_id == sci_ch.id
            print(f"Generated Question: {q.text} (Options: {q.options}, Correct: {q.correct_answer})")

        sci_ids = [q.id for q in sci_questions]

        # 6. Test Science Caching
        print("\n--- Testing Science Caching ---")
        cached_sci_questions = service.generate_ai_questions(sci_params)
        cached_sci_ids = [q.id for q in cached_sci_questions]
        assert sci_ids == cached_sci_ids, "Expected cached science questions to have same database IDs"
        print("Science Caching verification successful.")

        # 7. Test Science Regeneration
        print("\n--- Testing Science Regeneration ---")
        sci_params.regenerate = True
        regen_sci_questions = service.generate_ai_questions(sci_params)
        
        # Verify that the old science questions were deleted by checking total count in DB (should be 2, not 4)
        db_sci_count = db.query(Question).filter(Question.chapter_id == sci_ch.id).count()
        assert db_sci_count == 2, f"Expected 2 questions in DB after regeneration, found {db_sci_count}"
        assert len(regen_sci_questions) == 2
        print("Science Regeneration verification successful.")

        print("\n=== ALL TESTS PASSED SUCCESSFULLY ===")

    finally:
        db.close()

if __name__ == "__main__":
    test_ai_generation_pipeline()
