from typing import List
from sqlalchemy.orm import Session
from app.repositories.report_repository import ReportRepository
from app.models.report import Report
from app.core.exceptions import EntityNotFoundException

class ReportService:
    def __init__(self, db: Session):
        self.report_repo = ReportRepository(db)

    def get_report_by_id(self, report_id: int) -> Report:
        rep = self.report_repo.get_by_id(report_id)
        if not rep:
            raise EntityNotFoundException("Report", str(report_id))
        return rep

    def get_class_reports(self, class_id: int, tenant_id: str = None) -> List[Report]:
        return self.report_repo.get_by_class(class_id, tenant_id=tenant_id)

    def get_overview_statistics(self, tenant_id: str = None) -> dict:
        return self.report_repo.get_overview_stats(tenant_id=tenant_id)
