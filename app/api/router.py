from fastapi import APIRouter
from app.api.auth.routes import router as auth_router
from app.api.classes.routes import router as classes_router
from app.api.subjects.routes import router as subjects_router
from app.api.chapters.routes import router as chapters_router
from app.api.questions.routes import router as questions_router
from app.api.assessments.routes import router as assessments_router
from app.api.reports.routes import router as reports_router
from app.api.interviews.routes import router as interviews_router
from app.api.dashboard.routes import router as dashboard_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(classes_router, prefix="/classes", tags=["classes"])
api_router.include_router(subjects_router, prefix="/subjects", tags=["subjects"])
api_router.include_router(chapters_router, prefix="/chapters", tags=["chapters"])
api_router.include_router(questions_router, prefix="/questions", tags=["questions"])
api_router.include_router(assessments_router, prefix="/assessments", tags=["assessments"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

api_router.include_router(interviews_router, prefix="/interviews", tags=["interviews"])
