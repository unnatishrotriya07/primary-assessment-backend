from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user, enforce_super_admin
from app.schemas.class_schema import ClassCreate, ClassUpdate, ClassResponse
from app.services.class_service import ClassService

router = APIRouter()

@router.get("/", response_model=List[ClassResponse])
def read_classes(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ClassService(db)
    return service.get_all_classes()

@router.get("/{id}", response_model=ClassResponse)
def read_class(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ClassService(db)
    return service.get_class_by_id(id)

@router.post("/", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(class_in: ClassCreate, db: Session = Depends(get_db), current_user: dict = Depends(enforce_super_admin)):
    service = ClassService(db)
    return service.create_class(class_in)

@router.put("/{id}", response_model=ClassResponse)
def update_class(id: int, class_in: ClassUpdate, db: Session = Depends(get_db), current_user: dict = Depends(enforce_super_admin)):
    service = ClassService(db)
    return service.update_class(id, class_in)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(id: int, db: Session = Depends(get_db), current_user: dict = Depends(enforce_super_admin)):
    service = ClassService(db)
    service.delete_class(id)
    return None
