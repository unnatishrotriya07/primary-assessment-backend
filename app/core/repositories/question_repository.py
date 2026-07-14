from typing import List
from sqlalchemy.orm import Session
from app.models.question import Question

class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, tenant_id: str = None) -> List[Question]:
        query = self.db.query(Question)
        if tenant_id is not None:
            query = query.filter(Question.tenant_id == tenant_id)
        return query.all()

    def get_by_id(self, question_id: int, tenant_id: str = None) -> Question:
        query = self.db.query(Question).filter(Question.id == question_id)
        if tenant_id is not None:
            query = query.filter(Question.tenant_id == tenant_id)
        return query.first()

    def get_by_subject(self, subject_id: int, tenant_id: str = None) -> List[Question]:
        query = self.db.query(Question).filter(Question.subject_id == subject_id)
        if tenant_id is not None:
            query = query.filter(Question.tenant_id == tenant_id)
        return query.all()

    def create(self, question_obj: Question) -> Question:
        self.db.add(question_obj)
        self.db.commit()
        self.db.refresh(question_obj)
        return question_obj

    def delete(self, question_obj: Question) -> None:
        self.db.delete(question_obj)
        self.db.commit()
