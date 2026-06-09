from typing import List
from sqlalchemy.orm import Session
from app.repositories.chapter_repository import ChapterRepository
from app.schemas.chapter_schema import ChapterCreate, ChapterUpdate
from app.models.chapter import Chapter
from app.core.exceptions import EntityNotFoundException

class ChapterService:
    def __init__(self, db: Session):
        self.chapter_repo = ChapterRepository(db)

    def get_all_chapters(self, class_id: int = None, subject_id: int = None) -> List[Chapter]:
        return self.chapter_repo.get_filtered(class_id, subject_id)

    def get_chapter_by_id(self, chapter_id: int) -> Chapter:
        chap = self.chapter_repo.get_by_id(chapter_id)
        if not chap:
            raise EntityNotFoundException("Chapter", str(chapter_id))
        return chap

    def get_chapters_by_subject(self, subject_id: int) -> List[Chapter]:
        return self.chapter_repo.get_by_subject(subject_id)

    def create_chapter(self, chapter_in: ChapterCreate) -> Chapter:
        chap = Chapter(
            number=chapter_in.number,
            title=chapter_in.title,
            subject_id=chapter_in.subject_id,
            content=chapter_in.content
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
        return self.chapter_repo.update(chap)

    def delete_chapter(self, chapter_id: int) -> None:
        chap = self.get_chapter_by_id(chapter_id)
        self.chapter_repo.delete(chap)
