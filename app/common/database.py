from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.common.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# For SQLite, we need connect_args={"check_same_thread": False}
if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        db_url,
        pool_size=50,
        max_overflow=10,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Aggregate all models so Base has metadata
from app.core.models.school import School
from app.core.models.admin import Admin
from app.core.models.class_model import Class
from app.core.models.subject import Subject
from app.core.models.chapter import Chapter
from app.core.models.question import Question
from app.core.models.assessment import Assessment
from app.core.models.report import Report
from app.core.models.student_assessment import StudentAssessment
from app.core.models.interview import Interview, InterviewMessage, InterviewEvaluationStep, ConversationTurn  
from app.core.models.student import Student
from app.core.models.book import Book, BookChapter, ChapterSection, ChapterAsset
