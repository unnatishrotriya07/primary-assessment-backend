from typing import List
from sqlalchemy.orm import Session, selectinload
from app.models.assessment import Assessment
from app.models.student_assessment import StudentAssessment

class AssessmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Assessment]:
        return self.db.query(Assessment).options(
            selectinload(Assessment.assigned_students).selectinload(StudentAssessment.interview)
        ).all()

    def get_by_id(self, assessment_id: int) -> Assessment:
        return self.db.query(Assessment).filter(Assessment.id == assessment_id).options(
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
