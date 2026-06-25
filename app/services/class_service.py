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

    def get_or_create_class_section(self, base_class_id: int, section_name: str) -> Class:
        from app.models.class_model import Class
        from app.models.subject import Subject
        from app.models.chapter import Chapter

        # 1. Fetch base class
        base_cls = self.class_repo.get_by_id(base_class_id)
        if not base_cls:
            raise EntityNotFoundException("Class", str(base_class_id))

        # 2. Check if class with same name, grade, and section already exists
        existing_cls = self.class_repo.db.query(Class).filter(
            Class.name == base_cls.name,
            Class.grade == base_cls.grade,
            Class.section == section_name
        ).first()

        if existing_cls:
            return existing_cls

        # 3. Create new section class
        new_cls = Class(
            name=base_cls.name,
            grade=base_cls.grade,
            section=section_name
        )
        self.class_repo.db.add(new_cls)
        self.class_repo.db.commit()
        self.class_repo.db.refresh(new_cls)

        # 4. Copy subjects & chapters
        for subj in base_cls.subjects:
            new_code = f"{subj.code}_{section_name}"
            # Ensure unique code globally by appending index if duplicate exists
            base_code = new_code
            counter = 1
            while self.class_repo.db.query(Subject).filter(Subject.code == new_code).first() is not None:
                new_code = f"{base_code}_{counter}"
                counter += 1
            
            new_subj = Subject(
                name=subj.name,
                code=new_code,
                class_id=new_cls.id,
                status=subj.status
            )
            self.class_repo.db.add(new_subj)
            self.class_repo.db.commit()
            self.class_repo.db.refresh(new_subj)

            # Copy chapters
            for chap in subj.chapters:
                new_chap = Chapter(
                    number=chap.number,
                    title=chap.title,
                    subject_id=new_subj.id,
                    content=chap.content
                )
                self.class_repo.db.add(new_chap)
            
            self.class_repo.db.commit()

        # Re-fetch new class to load relationships
        return self.get_class_by_id(new_cls.id)
