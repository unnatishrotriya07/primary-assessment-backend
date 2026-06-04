from typing import List, Dict
import uuid
from sqlalchemy.orm import Session
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.assessment_schema import AssessmentCreate, SubmitAnswersParams, SubmissionResultResponse
from app.models.assessment import Assessment
from app.models.report import Report
from app.core.exceptions import EntityNotFoundException

class AssessmentService:
    def __init__(self, db: Session):
        self.assessment_repo = AssessmentRepository(db)
        self.question_repo = QuestionRepository(db)
        self.report_repo = ReportRepository(db)

    def get_all_assessments(self) -> List[Assessment]:
        return self.assessment_repo.get_all()

    def get_assessment_by_id(self, assessment_id: int) -> Assessment:
        asmt = self.assessment_repo.get_by_id(assessment_id)
        if not asmt:
            raise EntityNotFoundException("Assessment", str(assessment_id))
        return asmt

    def create_assessment(self, asmt_in: AssessmentCreate) -> Assessment:
        asmt = Assessment(
            title=asmt_in.title,
            subject_id=asmt_in.subject_id,
            class_id=asmt_in.class_id,
            status=asmt_in.status,
            date=asmt_in.date,
            questions_count=asmt_in.questions_count
        )
        if asmt_in.question_ids:
            from app.models.question import Question
            questions = self.assessment_repo.db.query(Question).filter(Question.id.in_(asmt_in.question_ids)).all()
            asmt.questions = questions
            asmt.questions_count = len(questions)
        return self.assessment_repo.create(asmt)

    def get_questions_for_session(self, assessment_id: int) -> list:
        asmt = self.get_assessment_by_id(assessment_id)
        if asmt.questions:
            return asmt.questions
        # Pull questions for subject
        all_q = self.question_repo.get_by_subject(asmt.subject_id)
        return all_q[:asmt.questions_count]

    def submit_session_answers(self, params: SubmitAnswersParams, db: Session) -> SubmissionResultResponse:
        # Mock parsing sessionId to find assessment
        # format of session_id: "asmt_{id}_{uuid}"
        parts = params.session_id.split("_")
        asmt_id = int(parts[1]) if len(parts) > 1 else 1
        
        asmt = self.get_assessment_by_id(asmt_id)
        questions = self.get_questions_for_session(asmt_id)
        
        from app.ai.answer_evaluator import AnswerEvaluator
        from app.ai.report_generator import ReportGenerator

        evaluator = AnswerEvaluator()
        report_gen = ReportGenerator()
        
        correct = 0
        total = len(questions)
        
        for q in questions:
            submitted = params.answers.get(str(q.id)) or ""
            eval_res = evaluator.evaluate(q, submitted)
            if eval_res.get("is_correct", False):
                correct += 1
                
        score = (correct / total * 100.0) if total > 0 else 0.0
        accuracy = score
        
        # Calculate grade
        if score >= 90: grade = "A"
        elif score >= 80: grade = "B"
        elif score >= 70: grade = "C"
        elif score >= 60: grade = "D"
        else: grade = "F"
        
        # Look up if this session is associated with an assigned StudentAssessment
        from app.models.student_assessment import StudentAssessment
        sa = db.query(StudentAssessment).filter(StudentAssessment.session_id == params.session_id).first()
        
        student_name = "Student User"
        student_email = None
        student_class = None
        date_of_birth = None
        contact = None
        
        if sa:
            student_name = sa.student_name
            student_email = sa.student_email
            student_class = sa.student_class
            date_of_birth = sa.date_of_birth
            contact = sa.contact
            sa.status = "Completed"
            db.commit()
            
        subject_name = asmt.subject.name if asmt.subject else ""
        class_name = asmt.target_class.name if asmt.target_class else ""
        
        # Generate personalized feedback using Gemini-2.0-flash
        feedback = report_gen.generate_report_feedback(
            score=score,
            accuracy=accuracy,
            class_name=class_name,
            subject_name=subject_name,
            student_name=student_name
        )
        
        # Create student report card
        report = Report(
            assessment_id=asmt.id,
            student_name=student_name,
            score=score,
            grade=grade,
            duration="12 mins",
            accuracy=accuracy,
            completed_at="Just now",
            feedback=feedback,
            student_email=student_email,
            student_class=student_class,
            date_of_birth=date_of_birth,
            contact=contact
        )
        self.report_repo.create(report)
        
        # Mark assessment status completed
        asmt.status = "Completed"
        self.assessment_repo.update(asmt)
        
        return SubmissionResultResponse(
            score=score,
            result_id=f"rep_{report.id}"
        )
