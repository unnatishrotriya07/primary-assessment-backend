from typing import Optional
from app.schemas.base_schema import CamelModel

class ChapterBase(CamelModel):
    number: str
    title: str
    subject_id: int
    content: Optional[str] = None
    text_content: Optional[str] = None

class ChapterCreate(ChapterBase):
    pass

class ChapterUpdate(CamelModel):
    number: Optional[str] = None
    title: Optional[str] = None
    subject_id: Optional[int] = None
    content: Optional[str] = None
    text_content: Optional[str] = None

class ChapterResponse(ChapterBase):
    id: int
    questions_count: Optional[int] = 0
