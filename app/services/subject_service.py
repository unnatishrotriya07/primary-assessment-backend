from typing import List
from sqlalchemy.orm import Session
from app.repositories.subject_repository import SubjectRepository
from app.schemas.subject_schema import SubjectCreate, SubjectUpdate
from app.models.subject import Subject
from app.core.exceptions import EntityNotFoundException, EntityAlreadyExistsException

class SubjectService:
    def __init__(self, db: Session):
        self.subject_repo = SubjectRepository(db)

    def get_all_subjects(self) -> List[Subject]:
        return self.subject_repo.get_all()

    def get_subject_by_id(self, subject_id: int) -> Subject:
        subj = self.subject_repo.get_by_id(subject_id)
        if not subj:
            raise EntityNotFoundException("Subject", str(subject_id))
        return subj

    def get_subjects_by_class(self, class_id: int) -> List[Subject]:
        return self.subject_repo.get_by_class(class_id)

    def create_subject(self, subject_in: SubjectCreate) -> Subject:
        if self.subject_repo.get_by_code(subject_in.code):
            raise EntityAlreadyExistsException("Subject", "code", subject_in.code)
        subj = Subject(
            name=subject_in.name,
            code=subject_in.code,
            class_id=subject_in.class_id,
            status=subject_in.status
        )
        return self.subject_repo.create(subj)

    def update_subject(self, subject_id: int, subject_in: SubjectUpdate) -> Subject:
        subj = self.get_subject_by_id(subject_id)
        if subject_in.name is not None:
            subj.name = subject_in.name
        if subject_in.code is not None and subject_in.code != subj.code:
            if self.subject_repo.get_by_code(subject_in.code):
                raise EntityAlreadyExistsException("Subject", "code", subject_in.code)
            subj.code = subject_in.code
        if subject_in.class_id is not None:
            subj.class_id = subject_in.class_id
        if subject_in.status is not None:
            subj.status = subject_in.status
        return self.subject_repo.update(subj)

    def delete_subject(self, subject_id: int) -> None:
        subj = self.get_subject_by_id(subject_id)
        self.subject_repo.delete(subj)
