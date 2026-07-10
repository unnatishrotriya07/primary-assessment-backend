from typing import List, Optional
from fastapi import APIRouter, Depends, status, File, UploadFile, HTTPException, BackgroundTasks
import io
from pypdf import PdfReader
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user, enforce_super_admin, check_admin_role
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
    return service.get_all_chapters(class_id=class_id, subject_id=subject_id, tenant_id=current_user.get("tenant_id"))

@router.get("/subject/{subject_id}", response_model=List[ChapterResponse])
def read_subject_chapters(subject_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ChapterService(db)
    return service.get_chapters_by_subject(subject_id, tenant_id=current_user.get("tenant_id"))

@router.get("/{id}", response_model=ChapterResponse)
def read_chapter(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ChapterService(db)
    chap = service.get_chapter_by_id(id)
    
    # Permission check for viewing individual chapter
    is_super_admin = (current_user.get("role") == "admin" and not current_user.get("tenant_id"))
    if not is_super_admin and chap.tenant_id and chap.tenant_id != current_user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Access denied.")
        
    return chap

@router.post("/parse-file")
def parse_chapter_file(file: UploadFile = File(...), current_user: dict = Depends(check_admin_role)):
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
def create_chapter(chapter_in: ChapterCreate, db: Session = Depends(get_db), current_user: dict = Depends(check_admin_role)):
    # Bind tenant_id to the created chapter if the user has a tenant_id
    if current_user.get("tenant_id"):
        chapter_in.tenant_id = current_user.get("tenant_id")
    service = ChapterService(db)
    return service.create_chapter(chapter_in)

@router.put("/{id}", response_model=ChapterResponse)
def update_chapter(id: int, chapter_in: ChapterUpdate, db: Session = Depends(get_db), current_user: dict = Depends(check_admin_role)):
    service = ChapterService(db)
    chap = service.get_chapter_by_id(id)
    
    # Permission check: Directors can only modify their own tenant's chapters. Global chapters require super-admin.
    is_super_admin = (current_user.get("role") == "admin" and not current_user.get("tenant_id"))
    if not is_super_admin:
        if chap.tenant_id != current_user.get("tenant_id"):
            raise HTTPException(status_code=403, detail="Access denied: Cannot modify this chapter.")
            
    return service.update_chapter(id, chapter_in)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter(id: int, db: Session = Depends(get_db), current_user: dict = Depends(check_admin_role)):
    service = ChapterService(db)
    chap = service.get_chapter_by_id(id)
    
    # Permission check
    is_super_admin = (current_user.get("role") == "admin" and not current_user.get("tenant_id"))
    if not is_super_admin:
        if chap.tenant_id != current_user.get("tenant_id"):
            raise HTTPException(status_code=403, detail="Access denied: Cannot delete this chapter.")
            
    service.delete_chapter(id)
    return None

@router.post("/{id}/sync-ncert", response_model=ChapterResponse)
def sync_ncert_chapter(
    id: int,
    background_tasks: BackgroundTasks,
    background: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(check_admin_role)
):
    service = ChapterService(db)
    if background:
        # Async Celery pipeline trigger
        try:
            from app.tasks.sync_tasks import sync_ncert_chapter_task
            sync_ncert_chapter_task.delay(id)
            print(f"[Routes] Enqueued sync task via Celery for chapter {id}", flush=True)
        except Exception as celery_err:
            print(f"[Routes] Celery connection failed: {celery_err}. Falling back to BackgroundTasks.", flush=True)
            
            # Use dedicated session in background thread
            def run_sync_in_background(chapter_id: int):
                from app.db.session import SessionLocal
                bg_db = SessionLocal()
                try:
                    bg_service = ChapterService(bg_db)
                    bg_service.sync_ncert_content(chapter_id)
                    print(f"[Background Task] Successfully synced NCERT content for chapter {chapter_id}", flush=True)
                except Exception as e:
                    print(f"[Background Task] NCERT sync failed for chapter {chapter_id}: {e}", flush=True)
                finally:
                    bg_db.close()
            
            background_tasks.add_task(run_sync_in_background, id)
            
        chap = service.get_chapter_by_id(id)
        return chap
    else:
        return service.sync_ncert_content(id)
