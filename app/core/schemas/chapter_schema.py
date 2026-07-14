from typing import List, Optional
from app.schemas.base_schema import CamelModel

class ChapterAssetResponse(CamelModel):
    id: int
    section_id: int
    asset_type: str
    image: str
    caption: Optional[str] = None

class ChapterSectionResponse(CamelModel):
    id: int
    chapter_id: int
    heading: str
    order: int
    html_content: str
    plain_text: str
    assets: List[ChapterAssetResponse] = []

class BookChapterResponse(CamelModel):
    id: int
    book_id: int
    chapter_number: int
    title: str
    slug: str
    summary: Optional[str] = None
    sections: List[ChapterSectionResponse] = []

class ChapterBase(CamelModel):
    number: str
    title: str
    subject_id: int
    content: Optional[str] = None
    text_content: Optional[str] = None
    tenant_id: Optional[str] = None
    book_chapter_id: Optional[int] = None

class ChapterCreate(ChapterBase):
    pass

class ChapterUpdate(CamelModel):
    number: Optional[str] = None
    title: Optional[str] = None
    subject_id: Optional[int] = None
    content: Optional[str] = None
    text_content: Optional[str] = None
    tenant_id: Optional[str] = None
    book_chapter_id: Optional[int] = None

class ChapterResponse(ChapterBase):
    id: int
    questions_count: Optional[int] = 0
    book_chapter: Optional[BookChapterResponse] = None
