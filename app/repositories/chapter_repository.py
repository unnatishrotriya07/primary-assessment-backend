from typing import List
from sqlalchemy.orm import Session
from app.models.chapter import Chapter

class ChapterRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Chapter]:
        return self.db.query(Chapter).all()

    def get_filtered(self, class_id: int = None, subject_id: int = None) -> List[Chapter]:
        from app.models.subject import Subject
        query = self.db.query(Chapter)
        if class_id is not None or subject_id is not None:
            query = query.join(Subject)
            if class_id is not None:
                query = query.filter(Subject.class_id == class_id)
            if subject_id is not None:
                query = query.filter(Chapter.subject_id == subject_id)
        return query.all()

    def get_by_id(self, chapter_id: int) -> Chapter:
        return self.db.query(Chapter).filter(Chapter.id == chapter_id).first()

    def get_by_subject(self, subject_id: int) -> List[Chapter]:
        return self.db.query(Chapter).filter(Chapter.subject_id == subject_id).all()

    def create(self, chapter_obj: Chapter) -> Chapter:
        self.db.add(chapter_obj)
        self.db.commit()
        self.db.refresh(chapter_obj)
        return chapter_obj

    def update(self, chapter_obj: Chapter) -> Chapter:
        self.db.commit()
        self.db.refresh(chapter_obj)
        return chapter_obj

    def delete(self, chapter_obj: Chapter) -> None:
        self.db.delete(chapter_obj)
        self.db.commit()
