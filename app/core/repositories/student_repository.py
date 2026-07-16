from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.student import Student

class StudentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Student]:
        return self.db.query(Student).all()

    def get_by_id(self, student_id: int) -> Optional[Student]:
        return self.db.query(Student).filter(Student.id == student_id).first()

    def get_by_scholar_number(self, scholar_number: str, tenant_id: Optional[str] = None) -> Optional[Student]:
        query = self.db.query(Student).filter(Student.scholar_number == scholar_number)
        if tenant_id:
            query = query.filter(Student.tenant_id == tenant_id)
        return query.first()

    def get_by_class(self, class_id: int, tenant_id: Optional[str] = None) -> List[Student]:
        query = self.db.query(Student).filter(Student.class_id == class_id)
        if tenant_id:
            query = query.filter(Student.tenant_id == tenant_id)
        return query.all()

    def create(self, student_obj: Student) -> Student:
        self.db.add(student_obj)
        self.db.commit()
        self.db.refresh(student_obj)
        return student_obj

    def update(self, student_obj: Student) -> Student:
        self.db.commit()
        self.db.refresh(student_obj)
        return student_obj

    def delete(self, student_obj: Student) -> None:
        self.db.delete(student_obj)
        self.db.commit()
