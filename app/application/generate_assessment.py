from sqlalchemy.orm import Session
from app.services.question_service import QuestionService
from app.schemas.question_schema import AIQuestionParams

class GenerateAssessmentUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, params: AIQuestionParams, tenant_id: str = None) -> list:
        service = QuestionService(self.db)
        return service.generate_ai_questions(params, tenant_id=tenant_id)
