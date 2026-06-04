from typing import Optional
from app.schemas.base_schema import CamelModel

class SubjectBase(CamelModel):
    name: str
    code: str
    class_id: int
    status: Optional[str] = "Active"

class SubjectCreate(SubjectBase):
    pass

class SubjectUpdate(CamelModel):
    name: Optional[str] = None
    code: Optional[str] = None
    class_id: Optional[int] = None
    status: Optional[str] = None

class SubjectResponse(SubjectBase):
    id: int
    chapters_count: Optional[int] = 0
