from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, nullable=False)
    title = Column(String, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    content = Column(String, nullable=True)
    text_content = Column(String, nullable=True)
    tenant_id = Column(String, nullable=True, index=True)

    subject = relationship("Subject", back_populates="chapters")
    questions = relationship("Question", back_populates="chapter", cascade="all, delete-orphan")
