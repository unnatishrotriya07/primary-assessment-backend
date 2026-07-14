from typing import List
from sqlalchemy.orm import Session, selectinload
from app.models.assessment import Assessment
from app.models.student_assessment import StudentAssessment

class AssessmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, tenant_id: str = None) -> List[Assessment]:
        query = self.db.query(Assessment)
        if tenant_id is not None:
            query = query.filter(Assessment.tenant_id == tenant_id)
        return query.options(
            selectinload(Assessment.assigned_students).selectinload(StudentAssessment.interview)
        ).all()

    def get_by_id(self, assessment_id: int, tenant_id: str = None) -> Assessment:
        query = self.db.query(Assessment).filter(Assessment.id == assessment_id)
        if tenant_id is not None:
            query = query.filter(Assessment.tenant_id == tenant_id)
        return query.options(
            selectinload(Assessment.assigned_students).selectinload(StudentAssessment.interview)
        ).first()

    def create(self, assessment_obj: Assessment) -> Assessment:
        self.db.add(assessment_obj)
        self.db.commit()
        self.db.refresh(assessment_obj)
        return assessment_obj

    def update(self, assessment_obj: Assessment) -> Assessment:
        self.db.commit()
        self.db.refresh(assessment_obj)
        return assessment_obj
