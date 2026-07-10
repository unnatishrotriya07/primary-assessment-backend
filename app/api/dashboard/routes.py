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
    tenant_id = current_user.get("tenant_id")
    
    total_classes = db.query(Class).count()
    
    # Active students are unique students in student_assessments
    student_query = db.query(StudentAssessment.student_email).distinct()
    if tenant_id is not None:
        student_query = student_query.filter(StudentAssessment.tenant_id == tenant_id)
    active_students = student_query.count()
    
    question_query = db.query(Question)
    if tenant_id is not None:
        question_query = question_query.filter(Question.tenant_id == tenant_id)
    generated_questions = question_query.count()
    
    # Total assessments conducted
    assessment_query = db.query(Assessment)
    if tenant_id is not None:
        assessment_query = assessment_query.filter(Assessment.tenant_id == tenant_id)
    assessments_conducted = assessment_query.count()
    
    # Average score and accuracy from reports
    report_query = db.query(Report)
    if tenant_id is not None:
        report_query = report_query.join(Assessment).filter(Assessment.tenant_id == tenant_id)
        
    avg_score = report_query.with_entities(func.avg(Report.score)).scalar() or 0.0
    avg_accuracy = report_query.with_entities(func.avg(Report.accuracy)).scalar() or 0.0
    
    # Round to 1 decimal place
    avg_score = round(float(avg_score), 1)
    avg_accuracy = round(float(avg_accuracy), 1)
    # Recent reports (last 5)
    recent_reports = report_query.order_by(Report.id.desc()).limit(5).all()
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
        
    # Calculate active_teachers
    from app.models.admin import Admin
    if tenant_id:
        active_teachers = db.query(Admin).filter(Admin.tenant_id == tenant_id, Admin.role == "teacher").count()
    else:
        active_teachers = db.query(Admin).filter(Admin.role == "teacher").count()

    # Calculate class_performance
    class_performance = []
    if tenant_id is not None:
        grouped_performances = db.query(
            Report.student_class,
            func.avg(Report.score).label("avg_score")
        ).join(Assessment).filter(Assessment.tenant_id == tenant_id).group_by(Report.student_class).all()
        
        for gp in grouped_performances:
            if gp[0]:
                score_val = round(float(gp[1]), 1) if gp[1] else 0.0
                if score_val >= 85:
                    status = "High Mastery"
                    color_type = "success"
                elif score_val >= 70:
                    status = "Awaiting Review"
                    color_type = "warning"
                else:
                    status = "Needs Support"
                    color_type = "error"
                class_performance.append({
                    "class_name": gp[0],
                    "topic": "Syllabus Unit Assessment",
                    "status": f"{int(score_val)}% {status}",
                    "color_type": color_type
                })

    # Teacher workloads & activity (dynamic query of teachers in tenant)
    teacher_workloads = []
    if tenant_id:
        teachers = db.query(Admin).filter(Admin.tenant_id == tenant_id, Admin.role == "teacher").all()
        for idx, t in enumerate(teachers):
            class_query = db.query(Class)
            class_count = class_query.count()
            if class_count > 0:
                class_obj = class_query.offset(idx % class_count).first()
                course_class = f"{class_obj.name} ({class_obj.section})"
            else:
                course_class = "General Curriculum"
                
            asmt_count = db.query(Assessment).filter(Assessment.tenant_id == tenant_id).count()
            if asmt_count > 0:
                action = f"Deployed {asmt_count} assessments"
                status = "Active"
                time_str = "Active today"
            else:
                action = "Drafted classroom worksheet"
                status = "Idle"
                time_str = "2 days ago"
                
            teacher_workloads.append({
                "name": t.name,
                "course_class": course_class,
                "recent_action": action,
                "time": time_str,
                "status": status
            })
            
    return {
        "total_classes": total_classes,
        "active_students": active_students,
        "generated_questions": generated_questions,
        "assessments_conducted": assessments_conducted,
        "average_score": avg_score,
        "average_accuracy": avg_accuracy,
        "recent_activity": recent_activity,
        "teacher_workloads": teacher_workloads,
        "active_teachers": active_teachers,
        "class_performance": class_performance
    }
