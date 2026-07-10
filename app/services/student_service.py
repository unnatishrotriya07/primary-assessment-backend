import uuid
import time
from typing import List, Dict, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.student_repository import StudentRepository
from app.repositories.class_repository import ClassRepository
from app.models.student import Student
from app.models.report import Report
from app.models.student_assessment import StudentAssessment
from app.schemas.student_schema import StudentUpdate
from app.core.exceptions import EntityNotFoundException
from app.utils.excel import parse_student_file
from app.utils.s3 import upload_to_s3

class StudentService:
    def __init__(self, db: Session):
        self.db = db
        self.student_repo = StudentRepository(db)
        self.class_repo = ClassRepository(db)

    def get_students(self, class_id: int, tenant_id: Optional[str] = None) -> List[Student]:
        return self.student_repo.get_by_class(class_id, tenant_id)

    def get_student_by_id(self, student_id: int, tenant_id: Optional[str] = None) -> Student:
        student = self.student_repo.get_by_id(student_id)
        if not student:
            raise EntityNotFoundException("Student", str(student_id))
        if tenant_id and student.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied to this student")
        return student

    def update_student(self, student_id: int, student_in: StudentUpdate, tenant_id: Optional[str] = None) -> Student:
        student = self.get_student_by_id(student_id, tenant_id)
        
        original_email = student.email
        
        # Check scholar number uniqueness if changing
        if student_in.scholar_number is not None and student_in.scholar_number != student.scholar_number:
            existing = self.student_repo.get_by_scholar_number(student_in.scholar_number)
            if existing and existing.id != student.id:
                raise HTTPException(status_code=400, detail=f"Scholar number '{student_in.scholar_number}' is already assigned to another student.")
        
        # Update attributes
        if student_in.name is not None:
            student.name = student_in.name
        if student_in.email is not None:
            student.email = student_in.email
        if student_in.contact_number is not None:
            student.contact_number = student_in.contact_number
        if student_in.scholar_number is not None:
            student.scholar_number = student_in.scholar_number
        if student_in.picture_url is not None:
            student.picture_url = student_in.picture_url
        if student_in.class_id is not None:
            # Verify new class exists
            cls = self.class_repo.get_by_id(student_in.class_id)
            if not cls:
                raise EntityNotFoundException("Class", str(student_in.class_id))
            student.class_id = student_in.class_id
        if student_in.teacher_notes is not None:
            student.teacher_notes = student_in.teacher_notes

        updated = self.student_repo.update(student)

        # Sync historical report emails if email changed
        if student_in.email is not None and student_in.email != original_email:
            try:
                self.db.query(Report).filter(Report.student_email == original_email).update({
                    Report.student_email: student_in.email
                }, synchronize_session=False)
                self.db.query(StudentAssessment).filter(StudentAssessment.student_email == original_email).update({
                    StudentAssessment.student_email: student_in.email
                }, synchronize_session=False)
                self.db.commit()
            except Exception as e:
                print(f"Error syncing historical emails: {e}", flush=True)
                self.db.rollback()

        return updated

    def delete_student(self, student_id: int, tenant_id: Optional[str] = None) -> None:
        student = self.get_student_by_id(student_id, tenant_id)
        self.student_repo.delete(student)

    def get_student_results(self, student_id: int, tenant_id: Optional[str] = None) -> List[dict]:
        student = self.get_student_by_id(student_id, tenant_id)
        
        # Query reports matching student email case-insensitively
        from sqlalchemy import func
        from app.models.interview import Interview
        from datetime import datetime

        reports = self.db.query(Report).filter(func.lower(Report.student_email) == func.lower(student.email)).all()
        
        # Query completed interviews matching student email case-insensitively
        interviews = self.db.query(Interview).join(
            StudentAssessment, Interview.student_assessment_id == StudentAssessment.id
        ).filter(
            func.lower(StudentAssessment.student_email) == func.lower(student.email),
            Interview.status == "Completed"
        ).all()

        combined = []

        # Map Reports
        for r in reports:
            # Try to parse completed_at for sorting. If it is "Just now", use current time.
            dt = None
            if r.completed_at:
                if r.completed_at == "Just now":
                    dt = datetime.utcnow()
                else:
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                        try:
                            dt = datetime.strptime(r.completed_at, fmt)
                            break
                        except ValueError:
                            continue
            if not dt:
                dt = datetime.min

            combined.append({
                "dt": dt,
                "data": {
                    "id": r.id,
                    "assessmentId": r.assessment_id,
                    "assessmentTitle": r.assessment.title if r.assessment else "Assessment",
                    "score": r.score,
                    "grade": r.grade,
                    "duration": r.duration,
                    "accuracy": r.accuracy,
                    "completedAt": r.completed_at,
                    "feedback": r.feedback
                }
            })

        # Map Interviews
        for iv in interviews:
            dt = iv.completed_at or datetime.min
            completed_at_str = iv.completed_at.strftime("%Y-%m-%d %H:%M:%S") if iv.completed_at else "Just now"
            feedback_str = iv.summary or iv.strengths or "No feedback available."

            combined.append({
                "dt": dt,
                "data": {
                    "id": iv.id + 1000000,  # Offset to prevent ID collisions with reports table in React keys
                    "assessmentId": iv.assessment_id,
                    "assessmentTitle": iv.assessment.title if iv.assessment else "Interview Assessment",
                    "score": iv.overall_score or 0.0,
                    "grade": iv.grade or "N/A",
                    "duration": "15 mins",  # Interview default duration
                    "accuracy": iv.overall_score or 0.0,
                    "completedAt": completed_at_str,
                    "feedback": feedback_str
                }
            })

        # Sort by datetime descending
        combined.sort(key=lambda x: x["dt"], reverse=True)

        return [item["data"] for item in combined]

    def import_students_excel(self, class_id: int, file_content: bytes, filename: str, tenant_id: Optional[str] = None) -> int:
        # Check if class exists
        cls = self.class_repo.get_by_id(class_id)
        if not cls:
            raise EntityNotFoundException("Class", str(class_id))

        # Parse Excel / CSV rows
        parsed_students = parse_student_file(file_content, filename)
        if not parsed_students:
            raise HTTPException(status_code=400, detail="No valid student rows found in the uploaded file.")

        import_count = 0
        for data in parsed_students:
            scholar_number = data["scholar_number"]
            name = data["name"]
            email = data["email"]
            contact_number = data["contact_number"]
            image_bytes = data["image_bytes"]

            picture_url = None
            if image_bytes:
                # Generate unique filename for S3
                unique_id = uuid.uuid4().hex[:8]
                timestamp = int(time.time())
                s3_filename = f"students/{scholar_number}_{unique_id}_{timestamp}.png"
                try:
                    picture_url = upload_to_s3(image_bytes, s3_filename, "image/png")
                except Exception as e:
                    print(f"Failed to upload image during excel import for scholar no {scholar_number}: {e}", flush=True)

            # Check if student with scholar number exists
            existing_student = self.student_repo.get_by_scholar_number(scholar_number)
            if existing_student:
                # Update details
                existing_student.name = name
                existing_student.email = email
                existing_student.contact_number = contact_number
                existing_student.class_id = class_id
                existing_student.tenant_id = tenant_id
                if picture_url:
                    existing_student.picture_url = picture_url
                self.student_repo.update(existing_student)
            else:
                # Create new student
                new_student = Student(
                    name=name,
                    email=email,
                    contact_number=contact_number,
                    scholar_number=scholar_number,
                    picture_url=picture_url,
                    class_id=class_id,
                    tenant_id=tenant_id
                )
                self.student_repo.create(new_student)
            
            import_count += 1

        return import_count

    def get_student_journey(self, student_id: int, tenant_id: Optional[str] = None) -> dict:
        student = self.get_student_by_id(student_id, tenant_id)
        
        # Fetch all subjects and chapters in the student's class
        from app.models.subject import Subject
        from app.models.chapter import Chapter
        from app.models.question import Question
        from app.models.report import Report
        from app.models.interview import Interview
        from app.models.student_assessment import StudentAssessment
        from app.models.assessment import Assessment, assessment_questions
        from sqlalchemy import func
        from datetime import datetime

        subjects = self.db.query(Subject).filter(Subject.class_id == student.class_id).all()
        
        # Get all completed reports & interviews for this student
        reports = self.db.query(Report).filter(func.lower(Report.student_email) == func.lower(student.email)).all()
        interviews = self.db.query(Interview).join(
            StudentAssessment, Interview.student_assessment_id == StudentAssessment.id
        ).filter(
            func.lower(StudentAssessment.student_email) == func.lower(student.email),
            Interview.status == "Completed"
        ).all()
        
        # Combine all assessments with their score, grade, date, subject, chapters
        completed_assessments = []
        for r in reports:
            dt = None
            if r.completed_at:
                if r.completed_at == "Just now":
                    dt = datetime.utcnow()
                else:
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                        try:
                            dt = datetime.strptime(r.completed_at, fmt)
                            break
                        except ValueError:
                            continue
            if not dt:
                dt = datetime.min
                
            completed_assessments.append({
                "type": "report",
                "id": r.id,
                "assessment_id": r.assessment_id,
                "assessment_title": r.assessment.title if r.assessment else "Assessment",
                "score": r.score,
                "grade": r.grade,
                "date": dt,
                "date_str": r.completed_at or "Just now",
                "feedback": r.feedback or "",
                "strengths": "",
                "improvements": "",
                "teacher_recommendations": "",
                "subscores": {}
            })
            
        for iv in interviews:
            dt = iv.completed_at or datetime.min
            completed_at_str = iv.completed_at.strftime("%Y-%m-%d %H:%M:%S") if iv.completed_at else "Just now"
            
            completed_assessments.append({
                "type": "interview",
                "id": iv.id,
                "assessment_id": iv.assessment_id,
                "assessment_title": iv.assessment.title if iv.assessment else "Interview Assessment",
                "score": iv.overall_score or 0.0,
                "grade": iv.grade or "N/A",
                "date": dt,
                "date_str": completed_at_str,
                "feedback": iv.summary or "Completed voice assessment.",
                "strengths": iv.strengths or "",
                "improvements": iv.improvements or "",
                "teacher_recommendations": iv.recommendation or "",
                "subscores": {
                    "communication": iv.score_communication or 70.0,
                    "numeracy": iv.score_numeracy or 70.0,
                    "creativity": iv.score_creativity or 70.0,
                    "emotionalIq": iv.score_emotional_iq or 70.0
                }
            })
            
        # Sort assessments by date ascending
        completed_assessments.sort(key=lambda x: x["date"])
        
        # Build subject mastery & chapter mastery mapping
        assessment_chapters = {}
        all_assessment_ids = [ca["assessment_id"] for ca in completed_assessments]
        if all_assessment_ids:
            questions_data = self.db.query(
                Assessment.id.label("assessment_id"),
                Chapter.id.label("chapter_id"),
                Chapter.title.label("chapter_title"),
                Chapter.number.label("chapter_number")
            ).join(
                assessment_questions, Assessment.id == assessment_questions.c.assessment_id
            ).join(
                Question, assessment_questions.c.question_id == Question.id
            ).join(
                Chapter, Question.chapter_id == Chapter.id
            ).filter(Assessment.id.in_(all_assessment_ids)).all()
            
            for qd in questions_data:
                if qd.assessment_id not in assessment_chapters:
                    assessment_chapters[qd.assessment_id] = set()
                assessment_chapters[qd.assessment_id].add(qd.chapter_id)
        
        subjects_data = []
        all_strengths = []
        all_improvements = []
        all_recommendations = []
        
        for ca in completed_assessments:
            if ca["strengths"]:
                all_strengths.append(ca["strengths"])
            if ca["improvements"]:
                all_improvements.append(ca["improvements"])
            if ca["teacher_recommendations"]:
                all_recommendations.append(ca["teacher_recommendations"])
                
        def get_chapter_num(ch_num):
            import re
            match = re.search(r'\d+', ch_num)
            return int(match.group()) if match else 999
            
        for sub in subjects:
            chaps = self.db.query(Chapter).filter(Chapter.subject_id == sub.id).all()
            chaps = sorted(chaps, key=lambda c: get_chapter_num(c.number))
            
            sub_assessments = [
                ca for ca in completed_assessments 
                if ca["assessment_id"] in [
                    a.id for a in self.db.query(Assessment).filter(Assessment.subject_id == sub.id).all()
                ]
            ]
            
            sub_score_avg = None
            if sub_assessments:
                sub_score_avg = sum([sa["score"] for sa in sub_assessments]) / len(sub_assessments)
                
            chapters_mastery = []
            for ch in chaps:
                ch_assessments = []
                for sa in sub_assessments:
                    ch_ids = assessment_chapters.get(sa["assessment_id"], set())
                    if ch.id in ch_ids:
                        ch_assessments.append(sa)
                
                ch_score = None
                status = "Not Started"
                if ch_assessments:
                    ch_score = sum([ca["score"] for ca in ch_assessments]) / len(ch_assessments)
                    status = "Mastered" if ch_score >= 75.0 else "In Progress"
                    
                chapters_mastery.append({
                    "id": ch.id,
                    "number": ch.number,
                    "title": ch.title,
                    "status": status,
                    "score": round(ch_score, 1) if ch_score is not None else None,
                    "assessmentsCount": len(ch_assessments)
                })
                
            current_ch = None
            suggested_next_ch = None
            
            for idx, ch_m in enumerate(chapters_mastery):
                if ch_m["status"] in ["In Progress", "Not Started"]:
                    current_ch = {"number": ch_m["number"], "title": ch_m["title"]}
                    if idx + 1 < len(chapters_mastery):
                        next_ch = chapters_mastery[idx + 1]
                        suggested_next_ch = {"number": next_ch["number"], "title": next_ch["title"]}
                    break
            
            if not current_ch and chapters_mastery:
                current_ch = {"number": "Completed", "title": "All chapters completed"}
                suggested_next_ch = {"number": "Advanced", "title": "Ready for next grade"}
                
            subjects_data.append({
                "subjectId": sub.id,
                "subjectName": sub.name,
                "subjectCode": sub.code,
                "masteryScore": round(sub_score_avg, 1) if sub_score_avg is not None else None,
                "currentChapter": current_ch,
                "suggestedNextChapter": suggested_next_ch,
                "chapters": chapters_mastery
            })
            
        timeline = []
        
        timeline.append({
            "type": "milestone",
            "date": getattr(student.school_class, "created_at").strftime("%Y-%m-%d") if (student.school_class and getattr(student.school_class, "created_at", None)) else "2026-06-01",
            "title": f"Started {student.school_class.name if student.school_class else 'Grade'}",
            "description": f"Academic learning path initiated for {student.name}."
        })
        
        for ca in completed_assessments:
            ach_unlocked = []
            if ca["score"] >= 90:
                ach_unlocked.append("Excellent Score")
            
            timeline.append({
                "type": "assessment",
                "date": ca["date_str"][:10],
                "title": f"Completed {ca['assessment_title']}",
                "description": ca["feedback"] or "Assessment completed.",
                "grade": ca["grade"],
                "score": ca["score"],
                "subscores": ca["subscores"],
                "achievements": ach_unlocked
            })
            
        achievements = []
        if len(completed_assessments) >= 1:
            achievements.append({
                "id": "ach_first_step",
                "title": "First Step Taken",
                "description": "Completed the first learning assessment successfully.",
                "type": "bronze",
                "date": completed_assessments[0]["date_str"][:10]
            })
        if len(completed_assessments) >= 3:
            achievements.append({
                "id": "ach_consistent",
                "title": "Consistent Explorer",
                "description": "Completed three or more evaluations on the platform.",
                "type": "silver",
                "date": completed_assessments[2]["date_str"][:10]
            })
            
        perfect_unlocked = False
        star_comm_unlocked = False
        creative_unlocked = False
        
        for ca in completed_assessments:
            if ca["score"] >= 95 and not perfect_unlocked:
                perfect_unlocked = True
                achievements.append({
                    "id": "ach_perfect",
                    "title": "Star Performer",
                    "description": f"Achieved a score of 95% or higher on {ca['assessment_title']}.",
                    "type": "gold",
                    "date": ca["date_str"][:10]
                })
            
            subscores = ca.get("subscores") or {}
            if subscores.get("communication", 0) >= 90 and not star_comm_unlocked:
                star_comm_unlocked = True
                achievements.append({
                    "id": "ach_communication",
                    "title": "Eloquent Speaker",
                    "description": f"Demonstrated high communication scores during {ca['assessment_title']}.",
                    "type": "gold",
                    "date": ca["date_str"][:10]
                })
                
            if subscores.get("creativity", 0) >= 90 and not creative_unlocked:
                creative_unlocked = True
                achievements.append({
                    "id": "ach_creativity",
                    "title": "Creative Explainer",
                    "description": f"Expressed complex topics in own words during {ca['assessment_title']}.",
                    "type": "silver",
                    "date": ca["date_str"][:10]
                })
                
        for sd in subjects_data:
            mastered_count = sum([1 for ch in sd["chapters"] if ch["status"] == "Mastered"])
            if mastered_count >= 1:
                achievements.append({
                    "id": f"ach_mastery_{sd['subjectId']}",
                    "title": f"{sd['subjectName']} Explorer",
                    "description": f"Successfully mastered chapters in {sd['subjectName']}.",
                    "type": "gold",
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
                
        parent_summary = ""
        best_subject = None
        best_subject_score = -1
        focus_subject = None
        focus_subject_score = 101
        
        for sd in subjects_data:
            if sd["masteryScore"] is not None:
                if sd["masteryScore"] > best_subject_score:
                    best_subject_score = sd["masteryScore"]
                    best_subject = sd["subjectName"]
                if sd["masteryScore"] < focus_subject_score:
                    focus_subject_score = sd["masteryScore"]
                    focus_subject = sd["subjectName"]
                    
        max_sub_skill = "understanding of topics"
        max_sub_val = -1
        skills_labels = {
            "communication": "verbal communication and clarity",
            "numeracy": "analytical reasoning and numbers",
            "creativity": "concept explanation and creativity",
            "emotionalIq": "self-expression and confidence"
        }
        
        for ca in completed_assessments:
            sub = ca.get("subscores") or {}
            for k, v in sub.items():
                if v > max_sub_val:
                    max_sub_val = v
                    max_sub_skill = skills_labels.get(k, max_sub_skill)
                    
        class_name = student.school_class.name if student.school_class else "class"
        
        if not completed_assessments:
            parent_summary = (
                f"{student.name} is embarking on their educational journey in {class_name}. "
                f"We are establishing baseline learning paths across subjects and look forward to "
                f"partnering with you to support their academic growth."
            )
        else:
            best_sub_str = f"especially in {best_subject}" if best_subject else ""
            skill_str = f"Their strong {max_sub_skill} helps them understand and explain concepts beautifully." if max_sub_val >= 80 else ""
            focus_sub_str = f"We are currently dedicating extra support to help them reinforce concepts in {focus_subject}." if focus_subject and focus_subject != best_subject else ""
            
            parent_summary = (
                f"{student.name} is showing positive progress in {class_name}. "
                f"They are engaging well with classroom assessments, {best_sub_str}. "
                f"{skill_str} "
                f"{focus_sub_str} "
                f"Overall, they are building steady academic foundations and showing positive improvement over time."
            )
            
        strengths_list = []
        improvements_list = []
        recs_list = []
        
        for s in all_strengths:
            for item in s.split("."):
                item_clean = item.strip().strip("-").strip("*").strip()
                if len(item_clean) > 10 and item_clean not in strengths_list:
                    strengths_list.append(item_clean)
                    if len(strengths_list) >= 4:
                        break
            if len(strengths_list) >= 4:
                break
                
        for imp in all_improvements:
            for item in imp.split("."):
                item_clean = item.strip().strip("-").strip("*").strip()
                if len(item_clean) > 10 and item_clean not in improvements_list:
                    improvements_list.append(item_clean)
                    if len(improvements_list) >= 4:
                        break
            if len(improvements_list) >= 4:
                break
                
        for rec in all_recommendations:
            for item in rec.split("."):
                item_clean = item.strip().strip("-").strip("*").strip()
                if len(item_clean) > 10 and item_clean not in recs_list:
                    recs_list.append(item_clean)
                    if len(recs_list) >= 4:
                        break
            if len(recs_list) >= 4:
                break
                
        if not completed_assessments:
            strengths_list = []
            improvements_list = []
            recs_list = []
        else:
            if not strengths_list:
                if best_subject:
                    strengths_list = [f"Strong concept understanding in {best_subject}.", "Expresses ideas clearly when explaining answers."]
                else:
                    strengths_list = ["Diligent worker during school exercises.", "Listens carefully and attempts all evaluation tasks."]
            if not improvements_list:
                improvements_list = ["Practice structured reasoning during open descriptions.", "Solve regular reinforcement worksheets on new topics."]
            if not recs_list:
                recs_list = ["Encourage peer explanations in classroom activities.", "Assign targeted chapter worksheets to solidify understanding."]
            
        teacher_notes = []
        if student.teacher_notes:
            teacher_notes = [note.strip() for note in student.teacher_notes.split("\n\n") if note.strip()]
            
        trend_data = []
        for ca in completed_assessments:
            entry = {
                "date": ca["date_str"][:10],
                "assessmentTitle": ca["assessment_title"],
                "overallScore": round(ca["score"], 1)
            }
            if ca["subscores"]:
                entry["communication"] = round(ca["subscores"]["communication"], 1)
                entry["numeracy"] = round(ca["subscores"]["numeracy"], 1)
                entry["creativity"] = round(ca["subscores"]["creativity"], 1)
                entry["emotionalIq"] = round(ca["subscores"]["emotionalIq"], 1)
            trend_data.append(entry)
            
        return {
            "student": {
                "id": str(student.id),
                "name": student.name,
                "email": student.email,
                "contactNumber": student.contact_number,
                "scholarNumber": student.scholar_number,
                "pictureUrl": student.picture_url,
                "classId": student.class_id,
                "teacherNotes": student.teacher_notes
            },
            "parentSummary": parent_summary,
            "strengths": strengths_list,
            "improvements": improvements_list,
            "teacherRecommendations": recs_list,
            "teacherNotes": teacher_notes,
            "achievements": achievements,
            "subjects": subjects_data,
            "timeline": timeline,
            "trendData": trend_data
        }
