import json
import pytest
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine, Base
from app.models.class_model import Class
from app.models.subject import Subject
from app.models.chapter import Chapter
from app.models.question import Question
from app.models.assessment import Assessment
from app.models.student import Student
from app.models.student_assessment import StudentAssessment
from app.models.interview import Interview, ConversationTurn
from app.services.interview_service import InterviewService
from app.services.compiler_service import AssessmentCompilerService

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_v2_conversation_engine_workflow(db_session: Session):
    # Clean up existing test token
    db_session.query(StudentAssessment).filter(StudentAssessment.token == "test-token-v2-12345").delete()
    db_session.commit()

    # Setup Class
    school_class = db_session.query(Class).first()
    if not school_class:
        school_class = Class(name="Grade 4")
        db_session.add(school_class)
        db_session.commit()
        db_session.refresh(school_class)

    # 1. Setup mock subject, chapter, and questions
    subject = db_session.query(Subject).first()
    if not subject:
        subject = Subject(name="Mathematics", code="MATH101")
        db_session.add(subject)
        db_session.commit()
        db_session.refresh(subject)

    chapter = db_session.query(Chapter).filter(Chapter.subject_id == subject.id).first()
    if not chapter:
        chapter = Chapter(number="1", title="Fractions", subject_id=subject.id, content="Intro to fractions")
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

    # Clean existing questions to ensure clean test
    db_session.query(Question).filter(Question.chapter_id == chapter.id).delete()
    db_session.commit()

    q1 = Question(
        text="What is a fraction?",
        options=[],
        correct_answer="A fraction represents a part of a whole.",
        question_type="tita",
        difficulty="easy",
        cognitive_level="remembering",
        subject_id=subject.id,
        chapter_id=chapter.id,
        generated_by="manual"
    )
    q2 = Question(
        text="What does the denominator represent?",
        options=[],
        correct_answer="The denominator represents the total number of equal parts.",
        question_type="tita",
        difficulty="medium",
        cognitive_level="understanding",
        subject_id=subject.id,
        chapter_id=chapter.id,
        generated_by="manual"
    )
    db_session.add(q1)
    db_session.add(q2)
    db_session.commit()

    # Create Assessment
    assessment = Assessment(
        title="Fractions Quick Quiz",
        subject_id=subject.id,
        class_id=school_class.id,
        status="Draft",
        questions_count=2,
        questions_to_ask=2
    )
    assessment.questions = [q1, q2]
    db_session.add(assessment)
    db_session.commit()

    # Create Student Assessment
    import datetime
    sa = StudentAssessment(
        assessment_id=assessment.id,
        student_name="Rahul Kumar",
        student_class="Grade 4",
        student_email="rahul@example.com",
        contact="1234567890",
        token="test-token-v2-12345",
        status="Pending",
        date_of_birth="2015-01-01",
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    )
    db_session.add(sa)
    db_session.commit()

    # 2. Start Interview & Verify compilation + session initialization
    service = InterviewService(db_session)
    res = service.start_interview("test-token-v2-12345", "rahul@example.com")
    
    interview_id = res["interview_id"]
    interview = db_session.query(Interview).filter(Interview.id == interview_id).first()
    assert interview is not None
    assert interview.session_state == "meet_buddy"
    assert interview.session_state_data is not None
    assert len(interview.session_state_data["questions"]) == 2

    # Verify compiled columns are filled
    compiled_q1 = db_session.query(Question).filter(Question.id == q1.id).first()
    assert compiled_q1.rubric is not None
    assert compiled_q1.hints is not None
    assert len(compiled_q1.hints) >= 1

    # Override session questions hints and followups for deterministic tests
    session_data = interview.session_state_data
    session_data["questions"][0]["hints"] = ["Clue 1: Think of slices."]
    session_data["questions"][0]["followups"] = ["Tell me more about parts."]
    session_data["questions"][1]["hints"] = []
    session_data["questions"][1]["followups"] = []
    interview.session_state_data = session_data
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(interview, "session_state_data")
    
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)

    # 3. Process turn: meet_buddy -> comfort_conv
    turn_res = service.process_turn(interview_id, "I am fine, thank you!")
    assert turn_res["next_state"] == "comfort_conv"
    assert "enjoy" in turn_res["next_speech"].lower()

    # 4. Process turn: comfort_conv (1) -> comfort_conv (2)
    turn_res = service.process_turn(interview_id, "I played football.")
    assert turn_res["next_state"] == "comfort_conv"
    assert "ready" in turn_res["next_speech"].lower()

    # 5. Process turn: comfort_conv (2) -> interview
    turn_res = service.process_turn(interview_id, "Yes, I am ready!")
    assert turn_res["next_state"] == "interview"
    assert "fraction" in turn_res["next_speech"].lower()
    assert turn_res["current_question_index"] == 0

    # 6. Process turn: interview -> HINT (simulate struggle)
    turn_res = service.process_turn(interview_id, "I don't know what it is.")
    assert turn_res["next_state"] == "HINT"
    assert turn_res["hints_remaining"] == 0
    assert turn_res["current_question_index"] == 0

    # 7. Process turn: HINT -> advances to next question (since student answers correctly)
    turn_res = service.process_turn(interview_id, "Ah, it means a part of a whole thing.")
    assert turn_res["next_state"] == "interview"
    assert turn_res["current_question_index"] == 1
    assert "denominator" in turn_res["next_speech"].lower()

    # 8. Process turn: interview -> GOODBYE (finish assessment)
    turn_res = service.process_turn(interview_id, "It means the total number of parts at the bottom.")
    assert turn_res["next_state"] == "GOODBYE"
    assert turn_res["completion_status"] == "Completed"

    # Verify ConversationTurn entries exist
    turns = db_session.query(ConversationTurn).filter(ConversationTurn.interview_id == interview_id).all()
    # Expect 6 turns: meet_buddy, comfort_conv (1), comfort_conv (2), question 1 (initial, hint), question 2
    assert len(turns) == 6
    for t in turns:
        assert t.student_transcript is not None
        assert t.buddy_message is not None
