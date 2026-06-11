# Import all the models, so that Base has them before being
# imported by Alembic or script runner.
from app.db.session import Base
from app.models.school import School
from app.models.admin import Admin
from app.models.class_model import Class
from app.models.subject import Subject
from app.models.chapter import Chapter
from app.models.question import Question
from app.models.assessment import Assessment
from app.models.report import Report
from app.models.student_assessment import StudentAssessment
from app.models.interview import Interview  
