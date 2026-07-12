import time
import os
import requests
import io
import shutil

BACKEND_URL = "http://localhost:5001/api/voice"

def test_integration():
    print("==================================================")
    print("Voice Engine End-to-End Integration Test Run")
    print("==================================================")

    results = {
        "Passed": [],
        "Failed": [],
        "Performance": {}
    }

    # 1. Health check verification
    try:
        t0 = time.time()
        res = requests.get(f"{BACKEND_URL}/health")
        latency = (time.time() - t0) * 1000
        if res.status_code == 200 and res.json().get("status") == "ok":
            results["Passed"].append("Health check GET /voice/health")
            results["Performance"]["Health check latency"] = f"{latency:.2f} ms"
        else:
            results["Failed"].append(f"Health check GET /voice/health (Status: {res.status_code})")
    except Exception as e:
        results["Failed"].append(f"Health check GET /voice/health (Error: {str(e)})")

    # 2. Kokoro speech generation (TTS)
    try:
        t0 = time.time()
        payload = {
            "text": "Hello, welcome to the Momentum educational assessment platform. Let's start with a quick question.",
            "voice": "af_bella",
            "speed": 1.0
        }
        res = requests.post(f"{BACKEND_URL}/speak", json=payload)
        latency = (time.time() - t0) * 1000
        if res.status_code == 200 and len(res.content) > 0:
            results["Passed"].append("Kokoro Speech generation /voice/speak (first synthesis)")
            results["Performance"]["Kokoro TTS initial synthesis"] = f"{latency:.2f} ms"
            first_content_len = len(res.content)
        else:
            results["Failed"].append(f"Kokoro Speech generation /voice/speak (Status: {res.status_code})")
    except Exception as e:
        results["Failed"].append(f"Kokoro Speech generation /voice/speak (Error: {str(e)})")

    # 3. Kokoro TTS Caching (should be almost instant)
    try:
        t0 = time.time()
        payload = {
            "text": "Hello, welcome to the Momentum educational assessment platform. Let's start with a quick question.",
            "voice": "af_bella",
            "speed": 1.0
        }
        res = requests.post(f"{BACKEND_URL}/speak", json=payload)
        latency = (time.time() - t0) * 1000
        if res.status_code == 200 and len(res.content) == first_content_len:
            results["Passed"].append("Kokoro Speech generation caching (subsequent requests)")
            results["Performance"]["Kokoro TTS cached synthesis"] = f"{latency:.2f} ms"
        else:
            results["Failed"].append("Kokoro Speech generation caching failed")
    except Exception as e:
        results["Failed"].append(f"Kokoro Speech generation caching error: {str(e)}")

    # 4. Whisper transcription (STT)
    # We will upload a simulated WAV header or small valid file if possible
    # Let's generate a minimal WAV container
    try:
        # 1 second of silence, 16kHz mono, 16-bit
        # WAV Header: RIFF (4 bytes), ChunkSize (4 bytes), WAVE (4 bytes), fmt  (4 bytes), Subchunk1Size (4 bytes)...
        wav_header = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
        
        t0 = time.time()
        files = {"file": ("test.wav", io.BytesIO(wav_header), "audio/wav")}
        res = requests.post(f"{BACKEND_URL}/transcribe", files=files)
        latency = (time.time() - t0) * 1000
        if res.status_code == 200:
            results["Passed"].append("Whisper Speech-to-Text /voice/transcribe")
            results["Performance"]["Whisper STT processing time"] = f"{latency:.2f} ms"
        else:
            results["Failed"].append(f"Whisper Speech-to-Text /voice/transcribe (Status: {res.status_code}, Res: {res.text})")
    except Exception as e:
        results["Failed"].append(f"Whisper Speech-to-Text /voice/transcribe (Error: {str(e)})")

    # 5. Invalid File Error Recovery
    try:
        files = {"file": ("badfile.txt", io.BytesIO(b"not an audio file"), "text/plain")}
        res = requests.post(f"{BACKEND_URL}/transcribe", files=files)
        if res.status_code == 400:
            results["Passed"].append("Error recovery for unsupported file formats")
        else:
            results["Failed"].append("Error recovery failed for unsupported formats")
    except Exception as e:
        results["Failed"].append(f"Error recovery check error: {str(e)}")

    # 6. Legacy TTS & STT Compatibility checking
    try:
        payload = {"text": "Legacy test", "voice_id": "af_bella", "speed": 1.0}
        res = requests.post(f"{BACKEND_URL}/tts", json=payload)
        if res.status_code == 200:
            results["Passed"].append("Legacy /voice/tts endpoint backward compatibility")
        else:
            results["Failed"].append("Legacy /voice/tts check failed")
    except Exception as e:
        results["Failed"].append(f"Legacy TTS check error: {str(e)}")

    # Report results
    print("\n--- RESULTS ---")
    print(f"Passed: {len(results['Passed'])}")
    for p in results["Passed"]:
        print(f" [+] {p}")
        
    print(f"Failed: {len(results['Failed'])}")
    for f in results["Failed"]:
        print(f" [-] {f}")

    print("\n--- PERFORMANCE DATA ---")
    for k, v in results["Performance"].items():
        print(f" * {k}: {v}")

    # Possible improvements suggestions
    print("\n==================================================")

if __name__ == "__main__":
    test_integration()
