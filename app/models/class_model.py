from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from app.db.session import Base

class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    grade = Column(String, nullable=False)
    section = Column(String, nullable=False)

    subjects = relationship("Subject", back_populates="school_class", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="school_class", cascade="all, delete-orphan")
