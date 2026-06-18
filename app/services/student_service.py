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
        
        # Query reports matching student email
        reports = self.db.query(Report).filter(Report.student_email == student.email).all()
        
        results = []
        for r in reports:
            results.append({
                "id": r.id,
                "assessmentId": r.assessment_id,
                "assessmentTitle": r.assessment.title if r.assessment else "Assessment",
                "score": r.score,
                "grade": r.grade,
                "duration": r.duration,
                "accuracy": r.accuracy,
                "completedAt": r.completed_at,
                "feedback": r.feedback
            })
        return results

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
