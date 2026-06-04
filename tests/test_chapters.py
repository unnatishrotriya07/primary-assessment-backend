import unittest
import unittest.mock
import io
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal, engine
from app.db.base import Base

class TestChaptersAPI(unittest.TestCase):
    def setUp(self):
        # Build clean test db tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

        # Seed admin user
        from app.models.admin import Admin
        from app.core.security import get_password_hash
        admin_user = Admin(
            name="Admin User",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123")
        )
        self.db.add(admin_user)
        self.db.commit()

        # Get login token
        login_res = self.client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "admin123"}
        )
        self.assertEqual(login_res.status_code, 200)
        self.token = login_res.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.db.close()

    def test_parse_txt_file_success(self):
        """Test successfully parsing a plain text file."""
        file_content = b"This is a mock textbook notes content for test chapters."
        file_obj = io.BytesIO(file_content)

        response = self.client.post(
            "/api/chapters/parse-file",
            files={"file": ("notes.txt", file_obj, "text/plain")},
            headers=self.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "This is a mock textbook notes content for test chapters.")
    @unittest.mock.patch("app.api.chapters.routes.PdfReader")
    def test_parse_pdf_file_success(self, mock_pdf_reader):
        """Test successfully parsing a PDF file using a mocked PdfReader."""
        # Setup mock reader behavior
        mock_page_1 = unittest.mock.MagicMock()
        mock_page_1.extract_text.return_value = "Page 1 Content"
        mock_page_2 = unittest.mock.MagicMock()
        mock_page_2.extract_text.return_value = "Page 2 Content"
        
        mock_reader_instance = unittest.mock.MagicMock()
        mock_reader_instance.pages = [mock_page_1, mock_page_2]
        mock_pdf_reader.return_value = mock_reader_instance

        file_content = b"%PDF-1.4 mock pdf data"
        file_obj = io.BytesIO(file_content)

        response = self.client.post(
            "/api/chapters/parse-file",
            files={"file": ("textbook.pdf", file_obj, "application/pdf")},
            headers=self.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "Page 1 Content\nPage 2 Content")
        mock_pdf_reader.assert_called_once()

    @unittest.mock.patch("app.api.chapters.routes.PdfReader")
    def test_parse_pdf_file_error(self, mock_pdf_reader):
        """Test that if PDF parsing throws an exception, it returns 400."""
        mock_pdf_reader.side_effect = Exception("Malformed PDF structure")

        file_content = b"corrupted pdf data"
        file_obj = io.BytesIO(file_content)

        response = self.client.post(
            "/api/chapters/parse-file",
            files={"file": ("corrupted.pdf", file_obj, "application/pdf")},
            headers=self.headers
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Failed to parse PDF", response.json()["detail"])
        self.assertIn("Malformed PDF structure", response.json()["detail"])

    def test_parse_unsupported_file_format(self):
        """Test uploading an unsupported format returns 400."""
        file_content = b"Mock image data"
        file_obj = io.BytesIO(file_content)

        response = self.client.post(
            "/api/chapters/parse-file",
            files={"file": ("diagram.png", file_obj, "image/png")},
            headers=self.headers
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file format", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
