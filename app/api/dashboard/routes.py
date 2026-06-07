from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.dependencies import get_db, get_current_user
from app.models.class_model import Class
from app.models.student_assessment import StudentAssessment
from app.models.question import Question
from app.models.assessment import Assessment
from app.models.report import Report

router = APIRouter()

@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    total_classes = db.query(Class).count()
    
    # Active students are unique students in student_assessments
    active_students = db.query(StudentAssessment.student_email).distinct().count()
    
    generated_questions = db.query(Question).count()
    
    # Total assessments conducted
    assessments_conducted = db.query(Assessment).count()
    
    # Average score and accuracy from reports
    avg_score = db.query(func.avg(Report.score)).scalar() or 0.0
    avg_accuracy = db.query(func.avg(Report.accuracy)).scalar() or 0.0
    
    # Round to 1 decimal place
    avg_score = round(float(avg_score), 1)
    avg_accuracy = round(float(avg_accuracy), 1)
    
    # Recent reports (last 5)
    recent_reports = db.query(Report).order_by(Report.id.desc()).limit(5).all()
    recent_activity = []
    for r in recent_reports:
        recent_activity.append({
            "id": r.id,
            "student_name": r.student_name,
            "student_class": r.student_class or "N/A",
            "score": float(r.score),
            "grade": r.grade,
            "accuracy": float(r.accuracy)
        })
        
    return {
        "total_classes": total_classes,
        "active_students": active_students,
        "generated_questions": generated_questions,
        "assessments_conducted": assessments_conducted,
        "average_score": avg_score,
        "average_accuracy": avg_accuracy,
        "recent_activity": recent_activity
    }
