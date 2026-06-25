from typing import List
from sqlalchemy.orm import Session
from app.repositories.chapter_repository import ChapterRepository
from app.schemas.chapter_schema import ChapterCreate, ChapterUpdate
from app.models.chapter import Chapter
from app.core.exceptions import EntityNotFoundException

class ChapterService:
    def __init__(self, db: Session):
        self.db = db
        self.chapter_repo = ChapterRepository(db)

    def get_all_chapters(self, class_id: int = None, subject_id: int = None, tenant_id: str = None) -> List[Chapter]:
        return self.chapter_repo.get_filtered(class_id, subject_id, tenant_id)

    def get_chapter_by_id(self, chapter_id: int) -> Chapter:
        chap = self.chapter_repo.get_by_id(chapter_id)
        if not chap:
            raise EntityNotFoundException("Chapter", str(chapter_id))
        return chap

    def get_chapters_by_subject(self, subject_id: int, tenant_id: str = None) -> List[Chapter]:
        return self.chapter_repo.get_by_subject(subject_id, tenant_id)

    def create_chapter(self, chapter_in: ChapterCreate) -> Chapter:
        chap = Chapter(
            number=chapter_in.number,
            title=chapter_in.title,
            subject_id=chapter_in.subject_id,
            content=chapter_in.content,
            text_content=chapter_in.text_content,
            tenant_id=chapter_in.tenant_id
        )
        return self.chapter_repo.create(chap)

    def update_chapter(self, chapter_id: int, chapter_in: ChapterUpdate) -> Chapter:
        chap = self.get_chapter_by_id(chapter_id)
        if chapter_in.number is not None:
            chap.number = chapter_in.number
        if chapter_in.title is not None:
            chap.title = chapter_in.title
        if chapter_in.subject_id is not None:
            chap.subject_id = chapter_in.subject_id
        if chapter_in.content is not None:
            chap.content = chapter_in.content
        if chapter_in.text_content is not None:
            chap.text_content = chapter_in.text_content
        return self.chapter_repo.update(chap)

    def delete_chapter(self, chapter_id: int) -> None:
        chap = self.get_chapter_by_id(chapter_id)
        self.chapter_repo.delete(chap)

    def sync_ncert_content(self, chapter_id: int) -> Chapter:
        from app.utils.ncert_sync import fetch_ncert_chapter_text
        from app.models.class_model import Class
        from app.models.subject import Subject
        
        chap = self.get_chapter_by_id(chapter_id)
        
        subject = self.db.query(Subject).filter(Subject.id == chap.subject_id).first()
        if not subject:
            raise EntityNotFoundException("Subject", str(chap.subject_id))
            
        cls = self.db.query(Class).filter(Class.id == subject.class_id).first()
        if not cls:
            raise EntityNotFoundException("Class", str(subject.class_id))
            
        text_content = fetch_ncert_chapter_text(cls.name, subject.name, chap.number)
        if text_content:
            chap.text_content = text_content
            self.chapter_repo.update(chap)
            
        return chap
