import unittest
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.student import Student
from app.models.class_model import Class
from app.core.services.student_service import StudentService

class TestStudentScholarUniqueness(unittest.TestCase):
    def setUp(self):
        # Reset DB tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        self.db = SessionLocal()
        self.service = StudentService(self.db)

        # Seed initial classes for different tenants
        self.class_school_a = Class(name="Grade 5-A", grade="5", section="A")
        self.class_school_b = Class(name="Grade 5-B", grade="5", section="B")
        self.db.add(self.class_school_a)
        self.db.add(self.class_school_b)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_scholar_number_unique_per_school(self):
        # 1. Add student to School A
        student_a = Student(
            name="Reyansh Mishra",
            email="reyansh@schoola.com",
            scholar_number="SCH260101",
            class_id=self.class_school_a.id,
            tenant_id="SCHOOL_A"
        )
        self.db.add(student_a)
        self.db.commit()

        # 2. Adding another student to School A with the same scholar number should trigger IntegrityError
        student_a_duplicate = Student(
            name="Rahul Sharma",
            email="rahul@schoola.com",
            scholar_number="SCH260101",
            class_id=self.class_school_a.id,
            tenant_id="SCHOOL_A"
        )
        self.db.add(student_a_duplicate)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        # 3. Adding a student to School B with the SAME scholar number should succeed
        student_b = Student(
            name="Reyansh Mishra",
            email="reyansh@schoolb.com",
            scholar_number="SCH260101",
            class_id=self.class_school_b.id,
            tenant_id="SCHOOL_B"
        )
        self.db.add(student_b)
        self.db.commit()  # Should not raise IntegrityError
        
        self.assertIsNotNone(student_b.id)

    def test_import_students_excel_uniqueness_validation(self):
        # 1. Add an existing student to School A
        student_a = Student(
            name="Reyansh Mishra",
            email="reyansh@schoola.com",
            scholar_number="SCH260101",
            class_id=self.class_school_a.id,
            tenant_id="SCHOOL_A"
        )
        self.db.add(student_a)
        self.db.commit()

        # 2. Try importing same scholar number to School A -> should fail validation in service
        from unittest.mock import patch
        mock_parsed = [
            {
                "scholar_number": "SCH260101",
                "name": "Duplicate Student",
                "email": "dup@schoola.com",
                "contact_number": "12345",
                "image_bytes": None
            }
        ]
        with patch("app.core.services.student_service.parse_student_file", return_value=mock_parsed):
            with self.assertRaises(HTTPException) as context:
                self.service.import_students_excel(
                    class_id=self.class_school_a.id,
                    file_content=b"dummy content",
                    filename="students.xlsx",
                    tenant_id="SCHOOL_A"
                )
            self.assertEqual(context.exception.status_code, 400)
            self.assertIn("already exists", context.exception.detail)

        # 3. Try importing same scholar number to School B -> should succeed
        with patch("app.core.services.student_service.parse_student_file", return_value=mock_parsed):
            count = self.service.import_students_excel(
                class_id=self.class_school_b.id,
                file_content=b"dummy content",
                filename="students.xlsx",
                tenant_id="SCHOOL_B"
            )
            self.assertEqual(count, 1)
