from typing import Optional
from app.schemas.base_schema import CamelModel

class ClassBase(CamelModel):
    name: str
    grade: str
    section: Optional[str] = "A"

class ClassCreate(ClassBase):
    pass

class ClassUpdate(CamelModel):
    name: Optional[str] = None
    grade: Optional[str] = None
    section: Optional[str] = None

class ClassResponse(ClassBase):
    id: int
    students_count: Optional[int] = 0
