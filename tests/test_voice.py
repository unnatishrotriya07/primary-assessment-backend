import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import io
import os
import shutil
from fastapi.testclient import TestClient

from app.main import app
from app.voice.whisper_service import get_whisper_service
from app.voice.kokoro_service import get_kokoro_service

class TestVoiceAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Clear singleton model cache to prevent cross-test interference
        get_whisper_service()._local_model = None
        
        # Clear Kokoro cache dir for isolation
        self.kokoro_service = get_kokoro_service()
        if os.path.exists(self.kokoro_service.cache_dir):
            shutil.rmtree(self.kokoro_service.cache_dir)
        os.makedirs(self.kokoro_service.cache_dir, exist_ok=True)

    def tearDown(self):
        get_whisper_service()._local_model = None
        if os.path.exists(self.kokoro_service.cache_dir):
            shutil.rmtree(self.kokoro_service.cache_dir)

    @patch("app.voice.whisper_service.WhisperService.is_available")
    @patch("app.voice.kokoro_service.KokoroService.is_available", new_callable=AsyncMock)
    def test_health_check_success(self, mock_kokoro, mock_whisper):
        """Test GET /voice/health returns ok status."""
        mock_whisper.return_value = True
        mock_kokoro.return_value = True
        response = self.client.get("/api/voice/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "whisper": "available", "kokoro": "available"})

    @patch("app.voice.whisper_service.WhisperModel")
    def test_transcribe_audio_success(self, MockWhisperModel):
        """Test successfully transcribing audio using faster-whisper mock."""
        # Setup mock model responses
        mock_model = MockWhisperModel.return_value
        
        mock_segment = MagicMock()
        mock_segment.text = "hello how are you"
        
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.duration = 2.5
        
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        # Create simulated audio file
        audio_content = b"RIFF....WAVEfmt ....data...."  # simulated WAV header/bytes
        audio_file = io.BytesIO(audio_content)

        response = self.client.post(
            "/api/voice/transcribe",
            files={"file": ("test.wav", audio_file, "audio/wav")}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["transcript"], "hello how are you")
        self.assertEqual(data["language"], "en")
        self.assertEqual(data["duration"], 2.5)
        self.assertIn("processing_time", data)

    def test_transcribe_audio_invalid_format(self):
        """Test validation error when passing unsupported audio formats."""
        audio_file = io.BytesIO(b"random text bytes")
        response = self.client.post(
            "/api/voice/transcribe",
            files={"file": ("test.txt", audio_file, "text/plain")}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported audio format", response.json()["detail"])

    @patch("app.voice.whisper_service.WhisperModel")
    def test_stt_endpoint_success(self, MockWhisperModel):
        """Test the legacy /voice/stt endpoint."""
        mock_model = MockWhisperModel.return_value
        mock_segment = MagicMock()
        mock_segment.text = "hello"
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.duration = 1.0
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        audio_file = io.BytesIO(b"fake wav bytes")
        response = self.client.post(
            "/api/voice/stt",
            files={"file": ("test.wav", audio_file, "audio/wav")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "hello")
        self.assertEqual(response.json()["language"], "en")

    @patch("app.voice.kokoro_service.httpx.AsyncClient")
    def test_tts_endpoint_success(self, MockAsyncClient):
        """Test text-to-speech audio synthesis endpoint."""
        mock_client = MockAsyncClient.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"synthesized audio bytes"
        mock_client.post.return_value = mock_response

        response = self.client.post(
            "/api/voice/tts",
            json={"text": "hello buddy", "voice_id": "af_bella", "speed": 1.0}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/mpeg")
        self.assertEqual(response.content, b"synthesized audio bytes")

    @patch("app.voice.kokoro_service.httpx.AsyncClient")
    def test_speak_endpoint_success_and_caching(self, MockAsyncClient):
        """Test speak endpoint success, chunking, and file-based caching."""
        # 1. Synthesize audio bytes
        mock_client = MockAsyncClient.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"[audio_chunk]"
        mock_client.post.return_value = mock_response

        # Request with multi-sentence text to trigger chunking
        payload = {
            "text": "Hello. How are you today? Let's begin.",
            "voice": "af_bella",
            "speed": 1.0
        }

        # First request (will trigger mock API calls)
        response1 = self.client.post("/api/voice/speak", json=payload)
        self.assertEqual(response1.status_code, 200)
        # It has three sentences, so it should trigger mock_client.post 3 times
        self.assertEqual(mock_client.post.call_count, 3)
        self.assertEqual(response1.content, b"[audio_chunk][audio_chunk][audio_chunk]")

        # Reset call count
        mock_client.post.reset_mock()

        # Second identical request (must load entirely from cache files, bypassing API call)
        response2 = self.client.post("/api/voice/speak", json=payload)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(mock_client.post.call_count, 0)  # zero HTTP requests made!
        self.assertEqual(response2.content, b"[audio_chunk][audio_chunk][audio_chunk]")

    def test_speak_endpoint_empty_input(self):
        """Test speak request fails with empty input."""
        response = self.client.post(
            "/api/voice/speak",
            json={"text": "  ", "voice": "af_bella"}
        )
        self.assertEqual(response.status_code, 502)  # maps to TTSException

    def test_transcribe_audio_empty(self):
        """Test validation error when passing empty audio file bytes."""
        audio_file = io.BytesIO(b"")
        response = self.client.post(
            "/api/voice/transcribe",
            files={"file": ("test.wav", audio_file, "audio/wav")}
        )
        self.assertEqual(response.status_code, 502)
        self.assertIn("Uploaded audio file is empty", response.json()["detail"])

