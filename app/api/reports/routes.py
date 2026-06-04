from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.schemas.report_schema import ReportResponse, ReportOverviewResponse
from app.services.report_service import ReportService

router = APIRouter()

@router.get("/overview", response_model=ReportOverviewResponse)
def read_reports_overview(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ReportService(db)
    stats = service.get_overview_statistics()
    return ReportOverviewResponse(
        total_students=stats["total_students"],
        passing_rate=stats["passing_rate"]
    )

@router.get("/class/{class_id}", response_model=List[ReportResponse])
def read_class_reports(class_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ReportService(db)
    return service.get_class_reports(class_id)

@router.get("/{id}", response_model=ReportResponse)
def read_report(id: int, db: Session = Depends(get_db)):
    service = ReportService(db)
    return service.get_report_by_id(id)
