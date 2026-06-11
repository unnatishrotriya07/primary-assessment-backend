import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, Float, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


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

    student_assessment = relationship("StudentAssessment", back_populates="interview")
    assessment         = relationship("Assessment")