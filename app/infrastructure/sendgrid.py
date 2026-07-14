import json
import logging
import urllib.request
import urllib.error
from app.common.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.SENDGRID_FROM_EMAIL

    def send_assessment_invitation(
        self,
        student_name: str,
        student_email: str,
        assessment_title: str,
        link: str,
        expires_at_str: str
    ) -> bool:
        """
        Sends assessment invitation email to the student using SendGrid v3 API.
        Falls back to log simulation if credentials are not configured.
        """
        if str(settings.SKIP_EMAIL).lower() == "true":
            logger.info(
                f"[SIMULATION] Email send skipped (SKIP_EMAIL=true). "
                f"Student: {student_name}, Email: {student_email}, Link: {link}"
            )
            return True

        if not self.api_key or not self.from_email:
            logger.warning(
                "SendGrid is not configured (SENDGRID_API_KEY or SENDGRID_FROM_EMAIL is empty). "
                "Email dispatch simulated."
            )
            return False

        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Build email content
        subject = f"You've been assigned an assessment: {assessment_title}"
        body_text = (
            f"Dear {student_name},\n\n"
            f"Your teacher has assigned you the assessment \"{assessment_title}\".\n\n"
            f"Please click the link below to access your assessment. Note that this link is only active for 24 hours "
            f"and can only be accessed once. You will be required to authenticate with your Google account "
            f"({student_email}) to verify your identity.\n\n"
            f"Assessment Access Link:\n"
            f"{link}\n\n"
            f"Expiration Date: {expires_at_str} UTC\n\n"
            f"Good luck!\n"
        )

        payload = {
            "personalizations": [
                {
                    "to": [{"email": student_email}],
                    "subject": subject
                }
            ],
            "from": {
                "email": self.from_email,
                "name": "Momentum Assessment Platform"
            },
            "content": [
                {
                    "type": "text/plain",
                    "value": body_text
                }
            ]
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req) as response:
                status_code = response.getcode()
                if status_code in (200, 201, 202):
                    logger.info(f"Successfully sent assessment invitation email to {student_email} via SendGrid.")
                    return True
                else:
                    logger.error(f"SendGrid returned unexpected status code: {status_code}")
                    return False
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode("utf-8")
                logger.error(f"SendGrid HTTP Error {e.code}: {e.reason} - Body: {error_body}")
            except Exception:
                logger.error(f"SendGrid HTTP Error {e.code}: {e.reason}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email to {student_email} via SendGrid: {str(e)}")
            return False
