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

    @unittest.mock.patch("sync_content.sync_chapter")
    def test_sync_ncert_chapter_success(self, mock_sync):
        """Test successfully syncing NCERT content for a chapter."""
        def fake_sync(db, book, chap_num, book_code, title, content):
            # Update the tenant chapter's text content
            from app.models.chapter import Chapter
            tenant_chap = db.query(Chapter).filter(Chapter.number == str(chap_num)).first()
            if tenant_chap:
                tenant_chap.text_content = "This is verified NCERT textbook chapter text."
                db.add(tenant_chap)
                db.commit()
        mock_sync.side_effect = fake_sync
        
        # Setup class and subject in DB
        from app.models.class_model import Class
        from app.models.subject import Subject
        from app.models.chapter import Chapter
        
        test_class = Class(name="Grade 10", grade="10", section="A")
        self.db.add(test_class)
        self.db.commit()
        
        test_subj = Subject(name="Mathematics", code="MATH10", class_id=test_class.id)
        self.db.add(test_subj)
        self.db.commit()
        
        test_chap = Chapter(number="1", title="Real Numbers", subject_id=test_subj.id)
        self.db.add(test_chap)
        self.db.commit()
        
        response = self.client.post(
            f"/api/chapters/{test_chap.id}/sync-ncert",
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["textContent"], "This is verified NCERT textbook chapter text.")
        
        # Verify db updated
        self.db.refresh(test_chap)
        self.assertEqual(test_chap.text_content, "This is verified NCERT textbook chapter text.")

    @unittest.mock.patch("app.api.chapters.routes.BackgroundTasks.add_task")
    @unittest.mock.patch("app.tasks.sync_tasks.sync_ncert_chapter_task.delay")
    def test_sync_ncert_chapter_background_success(self, mock_celery, mock_bg_tasks):
        """Test successfully triggering background NCERT sync."""
        # Setup class and subject in DB
        from app.models.class_model import Class
        from app.models.subject import Subject
        from app.models.chapter import Chapter
        
        test_class = Class(name="Grade 1", grade="1", section="A")
        self.db.add(test_class)
        self.db.commit()
        
        test_subj = Subject(name="Mathematics", code="MATH1", class_id=test_class.id)
        self.db.add(test_subj)
        self.db.commit()
        
        test_chap = Chapter(number="1", title="Shapes and Space", subject_id=test_subj.id)
        self.db.add(test_chap)
        self.db.commit()
        
        # Trigger background sync endpoint
        response = self.client.post(
            f"/api/chapters/{test_chap.id}/sync-ncert?background=true",
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        # Celery should be called with chapter id
        mock_celery.assert_called_once_with(test_chap.id)
        mock_bg_tasks.assert_not_called()

    @unittest.mock.patch("app.api.chapters.routes.BackgroundTasks.add_task")
    @unittest.mock.patch("app.tasks.sync_tasks.sync_ncert_chapter_task.delay")
    def test_sync_ncert_chapter_background_fallback(self, mock_celery, mock_bg_tasks):
        """Test background NCERT sync falls back to BackgroundTasks if Celery fails."""
        mock_celery.side_effect = Exception("Celery broker connection failed")
        
        # Setup class and subject in DB
        from app.models.class_model import Class
        from app.models.subject import Subject
        from app.models.chapter import Chapter
        
        test_class = Class(name="Grade 1", grade="1", section="A")
        self.db.add(test_class)
        self.db.commit()
        
        test_subj = Subject(name="Mathematics", code="MATH1", class_id=test_class.id)
        self.db.add(test_subj)
        self.db.commit()
        
        # We need a different chapter number to avoid collision
        test_chap = Chapter(number="2", title="Numbers from One to Nine", subject_id=test_subj.id)
        self.db.add(test_chap)
        self.db.commit()
        
        # Trigger background sync endpoint
        response = self.client.post(
            f"/api/chapters/{test_chap.id}/sync-ncert?background=true",
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        mock_celery.assert_called_once_with(test_chap.id)
        mock_bg_tasks.assert_called_once()

if __name__ == "__main__":
    unittest.main()
