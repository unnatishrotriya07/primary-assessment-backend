from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, JSON, DateTime, Text, Float
from sqlalchemy.orm import relationship
from app.common.database import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column("question", String, nullable=False)
    options = Column(JSON, nullable=False)  # Stored as JSON list of options
    correct_answer = Column("expected_answer", String, nullable=True)
    question_type = Column(String, default="mcq")
    difficulty = Column(String, nullable=False)  # easy, medium, hard
    cognitive_level = Column(String, nullable=False)  # remembering, applying, etc.
    
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    generated_by = Column(String, nullable=True)  # template, gemini, openai
    session = Column(String, nullable=True)  # academic or batch session identifier
    created_at = Column(DateTime, default=datetime.utcnow)
    tenant_id = Column(String, nullable=True)

    source = Column(String, nullable=True)
    section = Column(String, nullable=True)
    page = Column(String, nullable=True)
    confidence = Column(Integer, nullable=True)
    reference_text = Column(String, nullable=True)

    # V2 Compiler Fields
    learning_objective = Column(String, nullable=True)
    bloom_level = Column(String, nullable=True)
    expected_concepts = Column(JSON, nullable=True)
    rubric = Column(Text, nullable=True)
    common_mistakes = Column(JSON, nullable=True)
    hints = Column(JSON, nullable=True)
    followups = Column(JSON, nullable=True)
    maximum_followups = Column(Integer, default=2, nullable=False)
    minimum_coverage = Column(Float, default=0.6, nullable=False)
    ideal_answer_length = Column(Integer, default=50, nullable=False)
    estimated_duration = Column(Integer, default=120, nullable=False)
    scoring_rules = Column(Text, nullable=True)

    school_class = relationship("Class", back_populates="questions")
    subject = relationship("Subject", back_populates="questions")
    chapter = relationship("Chapter", back_populates="questions")
