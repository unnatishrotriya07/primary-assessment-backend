import uuid
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.schemas.student_schema import StudentResponse, StudentUpdate, StudentReportResponse
from app.services.student_service import StudentService
from app.utils.s3 import upload_to_s3

router = APIRouter()

@router.get("/", response_model=List[StudentResponse])
def read_students(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StudentService(db)
    return service.get_students(class_id=class_id, tenant_id=current_user.get("tenant_id"))

@router.get("/{id}", response_model=StudentResponse)
def read_student(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StudentService(db)
    return service.get_student_by_id(id, tenant_id=current_user.get("tenant_id"))

@router.put("/{id}", response_model=StudentResponse)
def update_student(
    id: int,
    student_in: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StudentService(db)
    return service.update_student(id, student_in, tenant_id=current_user.get("tenant_id"))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StudentService(db)
    service.delete_student(id, tenant_id=current_user.get("tenant_id"))
    return None

@router.get("/{id}/results", response_model=List[StudentReportResponse])
def read_student_results(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StudentService(db)
    return service.get_student_results(id, tenant_id=current_user.get("tenant_id"))

@router.post("/upload-excel", status_code=status.HTTP_201_CREATED)
async def upload_students_excel(
    class_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StudentService(db)
    content = await file.read()
    count = service.import_students_excel(
        class_id=class_id,
        file_content=content,
        filename=file.filename,
        tenant_id=current_user.get("tenant_id")
    )
    return {"message": f"Successfully imported {count} students.", "count": count}

@router.post("/{id}/picture", response_model=StudentResponse)
async def upload_student_picture(
    id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StudentService(db)
    # Check if student exists and belongs to tenant
    student = service.get_student_by_id(id, tenant_id=current_user.get("tenant_id"))
    
    # Upload to S3
    content = await file.read()
    unique_id = uuid.uuid4().hex[:8]
    timestamp = int(time.time())
    
    # Get file extension
    ext = "png"
    if file.filename and "." in file.filename:
        ext = file.filename.split(".")[-1].lower()
    
    s3_filename = f"students/{student.scholar_number}_{unique_id}_{timestamp}.{ext}"
    picture_url = upload_to_s3(content, s3_filename, file.content_type or "image/png")
    
    if not picture_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image to AWS S3. Please verify S3 bucket configuration and credentials in backend .env."
        )
    
    # Save URL in DB
    student_update = StudentUpdate(picture_url=picture_url)
    return service.update_student(id, student_update, tenant_id=current_user.get("tenant_id"))
