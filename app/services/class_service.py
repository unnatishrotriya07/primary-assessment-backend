from typing import List
from sqlalchemy.orm import Session
from app.repositories.class_repository import ClassRepository
from app.schemas.class_schema import ClassCreate, ClassUpdate
from app.models.class_model import Class
from app.core.exceptions import EntityNotFoundException

class ClassService:
    def __init__(self, db: Session):
        self.class_repo = ClassRepository(db)

    def get_all_classes(self, tenant_id: str = None) -> List[Class]:
        classes = self.class_repo.get_all()
        from app.models.student import Student
        for cls in classes:
            query = self.class_repo.db.query(Student).filter(Student.class_id == cls.id)
            if tenant_id:
                query = query.filter(Student.tenant_id == tenant_id)
            cls.students_count = query.count()
        return classes

    def get_class_by_id(self, class_id: int, tenant_id: str = None) -> Class:
        cls = self.class_repo.get_by_id(class_id)
        if not cls:
            raise EntityNotFoundException("Class", str(class_id))
        from app.models.student import Student
        query = self.class_repo.db.query(Student).filter(Student.class_id == cls.id)
        if tenant_id:
            query = query.filter(Student.tenant_id == tenant_id)
        cls.students_count = query.count()
        return cls

    def create_class(self, class_in: ClassCreate) -> Class:
        cls = Class(name=class_in.name, grade=class_in.grade, section=class_in.section)
        return self.class_repo.create(cls)

    def update_class(self, class_id: int, class_in: ClassUpdate) -> Class:
        cls = self.get_class_by_id(class_id)
        if class_in.name is not None:
            cls.name = class_in.name
        if class_in.grade is not None:
            cls.grade = class_in.grade
        if class_in.section is not None:
            cls.section = class_in.section
        return self.class_repo.update(cls)

    def delete_class(self, class_id: int) -> None:
        cls = self.get_class_by_id(class_id)
        self.class_repo.delete(cls)
