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
            tenant_id=chapter_in.tenant_id,
            book_chapter_id=chapter_in.book_chapter_id
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
        if chapter_in.book_chapter_id is not None:
            chap.book_chapter_id = chapter_in.book_chapter_id
        return self.chapter_repo.update(chap)

    def delete_chapter(self, chapter_id: int) -> None:
        chap = self.get_chapter_by_id(chapter_id)
        self.chapter_repo.delete(chap)

    def sync_ncert_content(self, chapter_id: int) -> Chapter:
        from app.models.class_model import Class
        from app.models.subject import Subject
        from app.models.book import Book
        from sync_content import sync_chapter
        
        chap = self.get_chapter_by_id(chapter_id)
        
        subject = self.db.query(Subject).filter(Subject.id == chap.subject_id).first()
        if not subject:
            raise EntityNotFoundException("Subject", str(chap.subject_id))
            
        cls = self.db.query(Class).filter(Class.id == subject.class_id).first()
        if not cls:
            raise EntityNotFoundException("Class", str(subject.class_id))
            
        # Find or create Book
        book = self.db.query(Book).filter(Book.class_ == cls.name, Book.subject == subject.name).first()
        if not book:
            from app.db.ncert_mapping import get_ncert_book_code
            book_code = get_ncert_book_code(cls.name, subject.name)
            if not book_code:
                raise ValueError(f"No NCERT book code found for Class: {cls.name}, Subject: {subject.name}")
            book = Book(
                class_=cls.name,
                subject=subject.name,
                title=f"{subject.name} for {cls.name}",
                language="Hindi" if subject.name.lower() == "hindi" else "English",
                edition="2026-27",
                source="NCERT"
            )
            self.db.add(book)
            self.db.commit()
            self.db.refresh(book)
            
        from app.db.ncert_mapping import get_ncert_book_code
        book_code = get_ncert_book_code(cls.name, subject.name)
        if not book_code:
            raise ValueError(f"No NCERT book code found for Class: {cls.name}, Subject: {subject.name}")
            
        sync_chapter(self.db, book, int(chap.number), book_code, chap.title, chap.content)
        
        self.db.refresh(chap)
        return chap
