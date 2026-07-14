from typing import List, Any
from pydantic import BaseModel

class Page(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int

def paginate(items: List[Any], page: int = 1, size: int = 10) -> Page:
    start = (page - 1) * size
    end = start + size
    sliced_items = items[start:end]
    return Page(
        items=sliced_items,
        total=len(items),
        page=page,
        size=size
    )
