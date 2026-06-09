from typing import List, Optional
from fastapi import APIRouter, Depends, status, File, UploadFile, HTTPException
import io
from pypdf import PdfReader
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.schemas.chapter_schema import ChapterCreate, ChapterUpdate, ChapterResponse
from app.services.chapter_service import ChapterService

router = APIRouter()

@router.get("/", response_model=List[ChapterResponse])
def read_chapters(
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = ChapterService(db)
    return service.get_all_chapters(class_id=class_id, subject_id=subject_id)

@router.get("/subject/{subject_id}", response_model=List[ChapterResponse])
def read_subject_chapters(subject_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ChapterService(db)
    return service.get_chapters_by_subject(subject_id)

@router.get("/{id}", response_model=ChapterResponse)
def read_chapter(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ChapterService(db)
    return service.get_chapter_by_id(id)

@router.post("/parse-file")
def parse_chapter_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    filename = file.filename.lower()
    if filename.endswith(".pdf"):
        try:
            content_bytes = file.file.read()
            pdf_file = io.BytesIO(content_bytes)
            reader = PdfReader(pdf_file)
            text_parts = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
            extracted_text = "\n".join(text_parts)
            return {"text": extracted_text}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    elif filename.endswith(".txt"):
        try:
            content_bytes = file.file.read()
            extracted_text = content_bytes.decode("utf-8")
            return {"text": extracted_text}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse TXT file: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a PDF or plain text (.txt) file.")

@router.post("/", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
def create_chapter(chapter_in: ChapterCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ChapterService(db)
    return service.create_chapter(chapter_in)

@router.put("/{id}", response_model=ChapterResponse)
def update_chapter(id: int, chapter_in: ChapterUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ChapterService(db)
    return service.update_chapter(id, chapter_in)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ChapterService(db)
    service.delete_chapter(id)
    return None
