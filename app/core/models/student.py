from sqlalchemy import Column, String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.common.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    contact_number = Column(String, nullable=True)
    scholar_number = Column(String, index=True, nullable=False)
    picture_url = Column(String, nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(String, ForeignKey("schools.tenant_id", ondelete="SET NULL"), nullable=True)
    teacher_notes = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint('scholar_number', 'tenant_id', name='uq_student_scholar_number_tenant'),
    )

    school_class = relationship("Class", backref="students")
