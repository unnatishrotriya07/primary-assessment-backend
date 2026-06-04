from sqlalchemy import Column, String, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.db.session import Base

# Association table for many-to-many relationship between Assessments and Questions
assessment_questions = Table(
    "assessment_questions",
    Base.metadata,
    Column("assessment_id", Integer, ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True),
    Column("question_id", Integer, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
)

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="Scheduled")  # Scheduled, Active, Completed
    date = Column(String, nullable=True)
    questions_count = Column(Integer, default=0)

    subject = relationship("Subject")
    target_class = relationship("Class")
    questions = relationship("Question", secondary=assessment_questions, backref="assessments")
