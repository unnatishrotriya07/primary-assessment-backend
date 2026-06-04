from typing import List
from sqlalchemy.orm import Session
from app.models.question import Question

class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Question]:
        return self.db.query(Question).all()

    def get_by_id(self, question_id: int) -> Question:
        return self.db.query(Question).filter(Question.id == question_id).first()

    def get_by_subject(self, subject_id: int) -> List[Question]:
        return self.db.query(Question).filter(Question.subject_id == subject_id).all()

    def create(self, question_obj: Question) -> Question:
        self.db.add(question_obj)
        self.db.commit()
        self.db.refresh(question_obj)
        return question_obj

    def delete(self, question_obj: Question) -> None:
        self.db.delete(question_obj)
        self.db.commit()
