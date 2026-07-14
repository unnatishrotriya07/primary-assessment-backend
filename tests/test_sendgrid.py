import unittest
import urllib.error
import urllib.request
from unittest.mock import patch, MagicMock
from io import BytesIO

from app.core.config import settings
from app.infrastructure.sendgrid import EmailService
from app.core.services.student_assessment_service import StudentAssessmentService
from app.schemas.student_assessment_schema import StudentAssessmentCreate
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.class_model import Class
from app.models.subject import Subject
from app.models.assessment import Assessment

class TestSendGridIntegration(unittest.TestCase):
    def setUp(self):
        # Reset DB tables for service tests
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()

        # Seed minimal entities
        self.test_class = Class(name="Grade 5", grade="5", section="A")
        self.db.add(self.test_class)
        self.db.commit()

        self.subject = Subject(name="Math", code="MATH5", status="Active", class_id=self.test_class.id)
        self.db.add(self.subject)
        self.db.commit()

        self.asmt = Assessment(
            title="Math Quiz",
            subject_id=self.subject.id,
            class_id=self.test_class.id,
            status="Active",
            date="2026-05-22",
            questions_count=1
        )
        self.db.add(self.asmt)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    @patch("app.infrastructure.sendgrid.settings")
    def test_sendgrid_simulation_fallback_when_credentials_missing(self, mock_settings):
        # Empty credentials
        mock_settings.SENDGRID_API_KEY = ""
        mock_settings.SENDGRID_FROM_EMAIL = ""

        service = EmailService()
        result = service.send_assessment_invitation(
            student_name="Test Student",
            student_email="student@example.com",
            assessment_title="Sample Assessment",
            link="http://localhost:3000/verify?token=123",
            expires_at_str="2026-05-23 00:00:00"
        )
        # Should return False (simulation mode)
        self.assertFalse(result)

    @patch("app.infrastructure.sendgrid.urllib.request.urlopen")
    @patch("app.infrastructure.sendgrid.settings")
    def test_sendgrid_dispatch_success(self, mock_settings, mock_urlopen):
        # Setup credentials
        mock_settings.SENDGRID_API_KEY = "SG.valid_test_key"
        mock_settings.SENDGRID_FROM_EMAIL = "sender@example.com"

        # Mock successful urlopen response (HTTP 202 Accepted)
        mock_response = MagicMock()
        mock_response.getcode.return_value = 202
        mock_urlopen.return_value.__enter__.return_value = mock_response

        service = EmailService()
        result = service.send_assessment_invitation(
            student_name="John Doe",
            student_email="john@example.com",
            assessment_title="Math Final",
            link="http://localhost:3000/verify?token=456",
            expires_at_str="2026-05-23 12:00:00"
        )

        self.assertTrue(result)
        mock_urlopen.assert_called_once()

    @patch("app.infrastructure.sendgrid.urllib.request.urlopen")
    @patch("app.infrastructure.sendgrid.settings")
    def test_sendgrid_http_error_graceful_handling(self, mock_settings, mock_urlopen):
        # Setup credentials
        mock_settings.SENDGRID_API_KEY = "SG.invalid_key"
        mock_settings.SENDGRID_FROM_EMAIL = "sender@example.com"

        # Mock HTTP Error from urlopen
        err_msg = b'{"errors": [{"message": "The provided authorization grant is invalid."}]}'
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.sendgrid.com/v3/mail/send",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(err_msg)
        )

        service = EmailService()
        result = service.send_assessment_invitation(
            student_name="John Doe",
            student_email="john@example.com",
            assessment_title="Math Final",
            link="http://localhost:3000/verify?token=456",
            expires_at_str="2026-05-23 12:00:00"
        )

        # Should handle error gracefully, return False, and not raise an exception
        self.assertFalse(result)

    @patch("app.core.services.student_assessment_service.EmailService")
    def test_assign_student_assessment_does_not_crash_on_email_failure(self, MockEmailClass):
        # Mock EmailService instance to simulate a failure
        mock_email_instance = MockEmailClass.return_value
        mock_email_instance.send_assessment_invitation.return_value = False

        sa_service = StudentAssessmentService(self.db)
        params = StudentAssessmentCreate(
            assessment_id=self.asmt.id,
            student_name="Robust Test",
            student_class="Grade 5A",
            date_of_birth="2015-05-20",
            student_email="robust@example.com",
            contact="1234567890"
        )

        # Assign assessment should complete successfully even if email delivery fails
        res = sa_service.assign_assessment(params)
        self.assertIsNotNone(res.id)
        self.assertEqual(res.student_name, "Robust Test")
        self.assertEqual(res.status, "Pending")

if __name__ == "__main__":
    unittest.main()
