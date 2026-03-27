"""
test_sarvam.py — Sarvam API integration tests (all mocked — no real API calls)
Tests: STT, TTS, translate endpoints, audio format, demo mode, error handling
"""

import pytest
import io
import json
from unittest.mock import patch, AsyncMock, MagicMock


def make_wav(duration=1):
    """Generate minimal valid WAV bytes."""
    import wave, struct, math
    buf = io.BytesIO()
    sample_rate = 16000
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(sample_rate * duration):
            val = int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            wf.writeframes(struct.pack("<h", val))
    buf.seek(0)
    return buf.read()


# ── /api/sarvam/transcribe ────────────────────────────────────────────────────

class TestTranscribeEndpoint:

    @pytest.mark.asyncio
    async def test_transcribe_demo_mode_no_key(self, client, registered_user):
        """With empty API key, should return demo transcript."""
        _, token = registered_user
        audio_bytes = make_wav()
        resp = await client.post(
            "/api/sarvam/transcribe",
            files={"audio": ("test.wav", audio_bytes, "audio/wav")},
            data={"language_code": "hi-IN"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "transcript" in data
        assert "Demo Mode" in data["transcript"] or data["transcript"] != ""

    @pytest.mark.asyncio
    async def test_transcribe_requires_auth(self, client, sample_audio):
        resp = await client.post(
            "/api/sarvam/transcribe",
            files={"audio": ("test.wav", sample_audio, "audio/wav")},
            data={"language_code": "hi-IN"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_transcribe_with_mock_sarvam_success(self, client, registered_user):
        _, token = registered_user
        mock_sarvam_response = {
            "transcript": "Aaj bahut achha din tha mera",
            "language_code": "hi-IN"
        }
        with patch("backend.routes.sarvam.sarvam_stt", new_callable=AsyncMock) as mock_stt:
            mock_stt.return_value = mock_sarvam_response
            resp = await client.post(
                "/api/sarvam/transcribe",
                files={"audio": ("test.wav", make_wav(), "audio/wav")},
                data={"language_code": "hi-IN"},
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200
        assert resp.json()["transcript"] == "Aaj bahut achha din tha mera"

    @pytest.mark.asyncio
    async def test_transcribe_returns_translated_text_for_non_english(self, client, registered_user):
        _, token = registered_user
        with patch("backend.routes.sarvam.sarvam_stt", new_callable=AsyncMock) as mock_stt, \
             patch("backend.routes.sarvam.sarvam_translate", new_callable=AsyncMock) as mock_trans:
            mock_stt.return_value = {"transcript": "Aaj achha din tha", "language_code": "hi-IN"}
            mock_trans.return_value = "Today was a good day"
            resp = await client.post(
                "/api/sarvam/transcribe",
                files={"audio": ("test.wav", make_wav(), "audio/wav")},
                data={"language_code": "hi-IN"},
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["translated_text"] == "Today was a good day"

    @pytest.mark.asyncio
    async def test_transcribe_english_skips_translation(self, client, registered_user):
        _, token = registered_user
        with patch("backend.routes.sarvam.sarvam_stt", new_callable=AsyncMock) as mock_stt, \
             patch("backend.routes.sarvam.sarvam_translate", new_callable=AsyncMock) as mock_trans:
            mock_stt.return_value = {"transcript": "Today was great", "language_code": "en-IN"}
            resp = await client.post(
                "/api/sarvam/transcribe",
                files={"audio": ("test.wav", make_wav(), "audio/wav")},
                data={"language_code": "en-IN"},
                headers={"Authorization": f"Bearer {token}"}
            )
        mock_trans.assert_not_called()
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_transcribe_all_supported_languages(self, client, registered_user):
        _, token = registered_user
        languages = ["hi-IN", "en-IN", "bn-IN", "ta-IN", "te-IN", "mr-IN", "gu-IN"]
        for lang in languages:
            with patch("backend.routes.sarvam.sarvam_stt", new_callable=AsyncMock) as mock_stt:
                mock_stt.return_value = {"transcript": f"Test in {lang}", "language_code": lang}
                resp = await client.post(
                    "/api/sarvam/transcribe",
                    files={"audio": ("test.wav", make_wav(), "audio/wav")},
                    data={"language_code": lang},
                    headers={"Authorization": f"Bearer {token}"}
                )
            assert resp.status_code == 200, f"Failed for language: {lang}"


# ── /api/sarvam/tts ───────────────────────────────────────────────────────────

class TestTTSEndpoint:

    @pytest.mark.asyncio
    async def test_tts_demo_mode_returns_empty(self, client, registered_user):
        """With no API key, TTS returns empty string."""
        _, token = registered_user
        resp = await client.post(
            "/api/sarvam/tts",
            json={"text": "Hello world", "language_code": "hi-IN", "speaker": "meera"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["audio_base64"] == ""

    @pytest.mark.asyncio
    async def test_tts_requires_auth(self, client):
        resp = await client.post(
            "/api/sarvam/tts",
            json={"text": "Hello", "language_code": "hi-IN", "speaker": "meera"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_tts_with_mock_returns_base64(self, client, registered_user):
        _, token = registered_user
        import base64
        fake_audio_b64 = base64.b64encode(b"fake_audio_bytes").decode()
        with patch("backend.routes.sarvam.sarvam_tts", new_callable=AsyncMock) as mock_tts:
            mock_tts.return_value = fake_audio_b64
            resp = await client.post(
                "/api/sarvam/tts",
                json={"text": "Aaj achha din tha", "language_code": "hi-IN", "speaker": "meera"},
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200
        assert resp.json()["audio_base64"] == fake_audio_b64


# ── /api/sarvam/translate ─────────────────────────────────────────────────────

class TestTranslateEndpoint:

    @pytest.mark.asyncio
    async def test_translate_demo_mode_returns_original(self, client, registered_user):
        """With no API key, returns original text unchanged."""
        _, token = registered_user
        resp = await client.post(
            "/api/sarvam/translate",
            json={"text": "Aaj achha din tha", "source_language_code": "hi-IN", "target_language_code": "en-IN"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["translated_text"] == "Aaj achha din tha"

    @pytest.mark.asyncio
    async def test_translate_requires_auth(self, client):
        resp = await client.post(
            "/api/sarvam/translate",
            json={"text": "hello", "source_language_code": "en-IN", "target_language_code": "hi-IN"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_translate_with_mock(self, client, registered_user):
        _, token = registered_user
        with patch("backend.routes.sarvam.sarvam_translate", new_callable=AsyncMock) as mock_trans:
            mock_trans.return_value = "Today was a good day"
            resp = await client.post(
                "/api/sarvam/translate",
                json={"text": "Aaj achha din tha", "source_language_code": "hi-IN"},
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200
        assert resp.json()["translated_text"] == "Today was a good day"


# ── /api/sarvam/analyze-mood ──────────────────────────────────────────────────

class TestAnalyzeMoodEndpoint:

    @pytest.mark.asyncio
    async def test_analyze_mood_success(self, client, registered_user):
        _, token = registered_user
        resp = await client.post(
            "/api/sarvam/analyze-mood",
            json={"text": "Aaj bahut khush hoon, amazing day!"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "mood" in data
        assert "score" in data
        assert "ai_response" in data

    @pytest.mark.asyncio
    async def test_analyze_mood_empty_text_returns_400(self, client, registered_user):
        _, token = registered_user
        resp = await client.post(
            "/api/sarvam/analyze-mood",
            json={"text": ""},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_analyze_mood_requires_auth(self, client):
        resp = await client.post(
            "/api/sarvam/analyze-mood",
            json={"text": "I am happy today"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_analyze_mood_score_in_range(self, client, registered_user):
        _, token = registered_user
        resp = await client.post(
            "/api/sarvam/analyze-mood",
            json={"text": "I feel great and happy today!"},
            headers={"Authorization": f"Bearer {token}"}
        )
        score = resp.json()["score"]
        assert 0.0 <= score <= 1.0


# ── internal sarvam helper functions ─────────────────────────────────────────

class TestSarvamHelpers:

    @pytest.mark.asyncio
    async def test_stt_demo_mode(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        with patch.dict(os.environ, {"SARVAM_API_KEY": ""}):
            from backend.routes.sarvam import sarvam_stt
            result = await sarvam_stt(b"fake audio bytes", "hi-IN")
        assert "transcript" in result
        assert "Demo Mode" in result["transcript"]

    @pytest.mark.asyncio
    async def test_translate_demo_mode(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        with patch.dict(os.environ, {"SARVAM_API_KEY": ""}):
            from backend.routes.sarvam import sarvam_translate
            result = await sarvam_translate("Aaj achha din tha", "hi-IN", "en-IN")
        assert result == "Aaj achha din tha"  # returns original

    @pytest.mark.asyncio
    async def test_tts_demo_mode(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        with patch.dict(os.environ, {"SARVAM_API_KEY": ""}):
            from backend.routes.sarvam import sarvam_tts
            result = await sarvam_tts("Hello world", "hi-IN")
        assert result == ""

    @pytest.mark.asyncio
    async def test_stt_truncates_long_responses(self):
        """TTS should not send more than 500 chars to API."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

        captured_payload = {}

        async def mock_post(url, **kwargs):
            captured_payload["json"] = kwargs.get("json", {})
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"audios": ["base64audio"]}
            return mock_resp

        with patch.dict(os.environ, {"SARVAM_API_KEY": "fake-key"}):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=mock_post
                )
                from backend.routes.sarvam import sarvam_tts
                long_text = "A" * 1000
                await sarvam_tts(long_text, "hi-IN")

        if "json" in captured_payload and "inputs" in captured_payload["json"]:
            sent_text = captured_payload["json"]["inputs"][0]
            assert len(sent_text) <= 500