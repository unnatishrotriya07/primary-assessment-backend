from typing import List
from sqlalchemy.orm import Session, selectinload
from app.models.subject import Subject

class SubjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Subject]:
        return self.db.query(Subject).options(selectinload(Subject.chapters)).all()

    def get_by_id(self, subject_id: int) -> Subject:
        return self.db.query(Subject).filter(Subject.id == subject_id).options(selectinload(Subject.chapters)).first()

    def get_by_class(self, class_id: int) -> List[Subject]:
        return self.db.query(Subject).filter(Subject.class_id == class_id).options(selectinload(Subject.chapters)).all()

    def get_by_code(self, code: str) -> Subject:
        return self.db.query(Subject).filter(Subject.code == code).options(selectinload(Subject.chapters)).first()

    def create(self, subject_obj: Subject) -> Subject:
        self.db.add(subject_obj)
        self.db.commit()
        self.db.refresh(subject_obj)
        return subject_obj

    def update(self, subject_obj: Subject) -> Subject:
        self.db.commit()
        self.db.refresh(subject_obj)
        return subject_obj

    def delete(self, subject_obj: Subject) -> None:
        self.db.delete(subject_obj)
        self.db.commit()
