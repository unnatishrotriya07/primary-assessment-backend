import unittest
from fastapi.testclient import TestClient

from app.main import app

class TestVoiceAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check_degraded(self):
        """Test GET /voice/health returns degraded/unavailable status since local engines are removed."""
        response = self.client.get("/api/voice/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "degraded")
        self.assertEqual(data["whisper"], "unavailable")
        self.assertEqual(data["kokoro"], "unavailable")

    def test_transcribe_audio_deprecated(self):
        """Test local transcription endpoint returns 502 due to deprecation."""
        response = self.client.post(
            "/api/voice/transcribe",
            files={"file": ("test.wav", b"fake audio bytes", "audio/wav")}
        )
        self.assertEqual(response.status_code, 502)
        self.assertIn("deprecated", response.json()["detail"])

    def test_stt_endpoint_deprecated(self):
        """Test local STT endpoint returns 502 due to deprecation."""
        response = self.client.post(
            "/api/voice/stt",
            files={"file": ("test.wav", b"fake audio bytes", "audio/wav")}
        )
        self.assertEqual(response.status_code, 502)
        self.assertIn("deprecated", response.json()["detail"])

    def test_tts_endpoint_deprecated(self):
        """Test local TTS endpoint returns 502 due to deprecation."""
        response = self.client.post(
            "/api/voice/tts",
            json={"text": "hello buddy", "voice_id": "af_bella", "speed": 1.0}
        )
        self.assertEqual(response.status_code, 502)
        self.assertIn("deprecated", response.json()["detail"])

    def test_speak_endpoint_deprecated(self):
        """Test local speak endpoint returns 502 due to deprecation."""
        response = self.client.post(
            "/api/voice/speak",
            json={"text": "hello buddy", "voice": "af_bella", "speed": 1.0}
        )
        self.assertEqual(response.status_code, 502)
        self.assertIn("deprecated", response.json()["detail"])
