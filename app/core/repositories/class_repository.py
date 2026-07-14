from typing import List
from sqlalchemy.orm import Session
from app.models.class_model import Class

class ClassRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Class]:
        return self.db.query(Class).all()

    def get_by_id(self, class_id: int) -> Class:
        return self.db.query(Class).filter(Class.id == class_id).first()

    def create(self, class_obj: Class) -> Class:
        self.db.add(class_obj)
        self.db.commit()
        self.db.refresh(class_obj)
        return class_obj

    def update(self, class_obj: Class) -> Class:
        self.db.commit()
        self.db.refresh(class_obj)
        return class_obj

    def delete(self, class_obj: Class) -> None:
        self.db.delete(class_obj)
        self.db.commit()
