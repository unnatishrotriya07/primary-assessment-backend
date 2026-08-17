import re
from datetime import datetime
from typing import List, Any, Optional
from pydantic import BaseModel
from fastapi.responses import JSONResponse

ENGLISH_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "in", "on", "at",
    "to", "for", "with", "by", "about", "like", "through", "over", "before",
    "after", "between", "under", "it", "this", "that", "these", "those",
    "or", "and", "but", "as", "if"
}

def is_valid_email(email: str) -> bool:
    regex = r"^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    return bool(re.match(regex, email))

def get_current_timestamp() -> str:
    return datetime.now().isoformat()

def success_response(data: Any, message: str = "Request completed successfully", status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data
        }
    )

def error_response(message: str, errors: Optional[Any] = None, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "errors": errors
        }
    )

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
