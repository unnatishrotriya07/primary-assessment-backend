from sqlalchemy.orm import Session
from app.services.interview_service import InterviewService

class StartInterviewUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, token: str, email: str) -> dict:
        service = InterviewService(self.db)
        return service.start_interview(token, email)
