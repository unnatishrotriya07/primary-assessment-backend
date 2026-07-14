from sqlalchemy.orm import Session
from app.ai_assessment.report.generator import EvaluationPipelineService

class GenerateReportUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, interview_id: int) -> dict:
        pipeline = EvaluationPipelineService(self.db)
        return pipeline.run_pipeline(interview_id)
