import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from app.common.database import Base


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)

    student_assessment_id = Column(
        Integer, ForeignKey("student_assessments.id", ondelete="CASCADE"), nullable=False
    )
    assessment_id = Column(
        Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )

    student_name  = Column(String, nullable=False)
    student_class = Column(String, nullable=False)

    # Full conversation saved as JSON string
    # shape: [{"role": "ai" or "student", "text": "...", "question_category": "..."}]
    transcript = Column(Text, nullable=True)

    # AI scores — filled after student submits
    overall_score       = Column(Float,  nullable=True)
    grade               = Column(String, nullable=True)   # A+, A, B+, B, C
    recommendation      = Column(String, nullable=True)   # Strongly Recommended / Recommended / Needs Review
    score_communication = Column(Float,  nullable=True)
    score_numeracy      = Column(Float,  nullable=True)
    score_creativity    = Column(Float,  nullable=True)
    score_emotional_iq  = Column(Float,  nullable=True)

    strengths    = Column(Text, nullable=True)
    improvements = Column(Text, nullable=True)
    admin_note   = Column(Text, nullable=True)
    summary      = Column(Text, nullable=True)
    evaluated_answers = Column(JSON, nullable=True)

    status       = Column(String, default="In Progress")  # In Progress | Completed
    started_at   = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # V2 Engine metadata
    language         = Column(String, nullable=True, default="en-US")
    confidence       = Column(Float, nullable=True)
    audio_references = Column(JSON, nullable=True)
    report_version   = Column(String, nullable=True, default="2.0.0")

    # Session state management
    current_question_index = Column(Integer, default=0, nullable=False)
    session_state          = Column(String, default="meet_buddy", nullable=False)
    comfort_index          = Column(Integer, default=0, nullable=False)
    raw_answers            = Column(JSON, nullable=True)
    network_status         = Column(String, default="online", nullable=False)
    completion_status      = Column(String, default="In Progress", nullable=False)
    session_state_data     = Column(JSON, nullable=True)

    # Human Review mode
    requires_review        = Column(Boolean, default=False, nullable=False)
    review_reason          = Column(String, nullable=True)
    reviewed_by            = Column(String, nullable=True)
    reviewed_at            = Column(DateTime, nullable=True)

    # Transcript progress
    raw_transcript         = Column(Text, nullable=True)
    clean_transcript       = Column(Text, nullable=True)
    validated_transcript   = Column(Text, nullable=True)

    student_assessment = relationship("StudentAssessment", back_populates="interview")
    assessment         = relationship("Assessment")

    messages           = relationship("InterviewMessage", back_populates="interview", cascade="all, delete-orphan")
    evaluation_steps   = relationship("InterviewEvaluationStep", back_populates="interview", cascade="all, delete-orphan")
    conversation_turns = relationship("ConversationTurn", back_populates="interview", cascade="all, delete-orphan")


class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(
        Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String, nullable=False)  # "ai" or "student"
    text = Column(Text, nullable=False)
    question_category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # V2 Sequence and Speech parameters
    sequence_number = Column(Integer, nullable=True)
    question_id = Column(Integer, nullable=True)
    student_response = Column(Text, nullable=True)
    buddy_response = Column(Text, nullable=True)
    audio_url = Column(String, nullable=True)
    speech_confidence = Column(Float, nullable=True)

    interview = relationship("Interview", back_populates="messages")


class InterviewEvaluationStep(Base):
    __tablename__ = "interview_evaluation_steps"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(
        Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False
    )
    step_name = Column(String, nullable=False)  # e.g., "transcript_cleanup", "question_mapping", etc.
    status = Column(String, default="Pending")  # Pending | Running | Completed | Failed
    output = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    interview = relationship("Interview", back_populates="evaluation_steps")


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(
        Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(String, nullable=True)
    buddy_message = Column(Text, nullable=True)
    student_transcript = Column(Text, nullable=True)
    audio_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    interview = relationship("Interview", back_populates="conversation_turns")