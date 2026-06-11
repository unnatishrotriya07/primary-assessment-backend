from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user, enforce_super_admin
from app.schemas.subject_schema import SubjectCreate, SubjectUpdate, SubjectResponse
from app.services.subject_service import SubjectService
from app.schemas.chapter_schema import ChapterResponse
from app.services.chapter_service import ChapterService

router = APIRouter()

@router.get("/", response_model=List[SubjectResponse])
def read_subjects(class_id: Optional[int] = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = SubjectService(db)
    if class_id is not None:
        return service.get_subjects_by_class(class_id)
    return service.get_all_subjects()

@router.get("/{id}", response_model=SubjectResponse)
def read_subject(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = SubjectService(db)
    return service.get_subject_by_id(id)

@router.get("/{subject_id}/chapters", response_model=List[ChapterResponse])
def read_subject_chapters(subject_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ChapterService(db)
    return service.get_chapters_by_subject(subject_id)

@router.post("/", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(subject_in: SubjectCreate, db: Session = Depends(get_db), current_user: dict = Depends(enforce_super_admin)):
    service = SubjectService(db)
    return service.create_subject(subject_in)

@router.put("/{id}", response_model=SubjectResponse)
def update_subject(id: int, subject_in: SubjectUpdate, db: Session = Depends(get_db), current_user: dict = Depends(enforce_super_admin)):
    service = SubjectService(db)
    return service.update_subject(id, subject_in)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(id: int, db: Session = Depends(get_db), current_user: dict = Depends(enforce_super_admin)):
    service = SubjectService(db)
    service.delete_subject(id)
    return None
