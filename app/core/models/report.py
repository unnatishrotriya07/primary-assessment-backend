from sqlalchemy import Column, String, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.session import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    student_name = Column(String, nullable=False)
    score = Column(Float, nullable=False)  # Percentage score
    grade = Column(String, nullable=False)  # A, B, C, D, etc.
    duration = Column(String, nullable=False)  # Duration formatted e.g. "45 mins"
    accuracy = Column(Float, nullable=False)  # Accuracy percentage
    completed_at = Column(String, nullable=True)
    feedback = Column(String, nullable=True)
    student_email = Column(String, nullable=True)
    student_class = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)
    contact = Column(String, nullable=True)

    assessment = relationship("Assessment")
