import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base

class StudentAssessment(Base):
    __tablename__ = "student_assessments"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    student_name = Column(String, nullable=False)
    student_class = Column(String, nullable=False)
    date_of_birth = Column(String, nullable=False)  # Stores YYYY-MM-DD format
    student_email = Column(String, nullable=False)
    contact = Column(String, nullable=False)  # Contact number
    token = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    session_id = Column(String, nullable=True)  # Linked active session ID
    status = Column(String, default="Pending")  # Pending, Started, Completed, Expired

    assessment = relationship("Assessment", back_populates="assigned_students")
    interview = relationship("Interview", back_populates="student_assessment", uselist=False, cascade="all, delete-orphan")
