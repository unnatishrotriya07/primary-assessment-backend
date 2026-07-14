from sqlalchemy.orm import Session
from app.services.interview_service import InterviewService
from app.schemas.interview_schema import InterviewSubmitRequest
from app.core.models.interview import Interview

class SubmitResponseUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, payload: InterviewSubmitRequest) -> Interview:
        service = InterviewService(self.db)
        return service.save_submission_and_set_evaluating(payload)
