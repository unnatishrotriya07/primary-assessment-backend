from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.report import Report

class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Report]:
        return self.db.query(Report).all()

    def get_by_id(self, report_id: int) -> Report:
        return self.db.query(Report).filter(Report.id == report_id).first()

    def get_by_class(self, class_id: int, tenant_id: str = None) -> List[Report]:
        # Connects through assessment target class
        from app.models.assessment import Assessment
        query = self.db.query(Report).join(Assessment).filter(Assessment.class_id == class_id)
        if tenant_id is not None:
            query = query.filter(Assessment.tenant_id == tenant_id)
        return query.all()

    def create(self, report_obj: Report) -> Report:
        self.db.add(report_obj)
        self.db.commit()
        self.db.refresh(report_obj)
        return report_obj

    def get_overview_stats(self, tenant_id: str = None) -> dict:
        from app.models.assessment import Assessment
        
        query_total = self.db.query(func.count(Report.id))
        query_passing = self.db.query(func.count(Report.id)).filter(Report.score >= 40.0)
        
        if tenant_id is not None:
            query_total = query_total.join(Assessment).filter(Assessment.tenant_id == tenant_id)
            query_passing = query_passing.join(Assessment).filter(Assessment.tenant_id == tenant_id)
            
        total_students = query_total.scalar() or 0
        passing_students = query_passing.scalar() or 0
        passing_rate = (passing_students / total_students * 100) if total_students > 0 else 0.0

        return {
            "total_students": total_students,
            "passing_rate": passing_rate
        }
