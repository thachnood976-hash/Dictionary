import base64
import json
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from dictionary_app.tts import PhoneticsService


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class TtsTests(TestCase):
    def test_generate_audio_uses_gemini_and_writes_wav(self) -> None:
        pcm_bytes = (b"\x00\x00\x01\x00" * 100)
        payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/L16;rate=24000",
                                    "data": base64.b64encode(pcm_bytes).decode("ascii"),
                                }
                            }
                        ]
                    }
                }
            ]
        }

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            service = PhoneticsService(
                tmp_path / "phonetic_cache.json",
                tmp_path / "audio_cache",
                api_key="test-key",
                tts_model="gemini-2.5-flash-preview-tts",
                tts_voice="Kore",
            )

            with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
                audio_path = service.generate_audio("biology")

            self.assertTrue(audio_path.exists())
            with wave.open(str(audio_path), "rb") as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getframerate(), 24000)
                self.assertEqual(handle.getsampwidth(), 2)
                self.assertEqual(handle.readframes(handle.getnframes()), pcm_bytes)

    def test_generate_audio_sends_plain_transcript_to_tts(self) -> None:
        pcm_bytes = (b"\x00\x00\x01\x00" * 10)
        payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/L16;rate=24000",
                                    "data": base64.b64encode(pcm_bytes).decode("ascii"),
                                }
                            }
                        ]
                    }
                }
            ]
        }

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            service = PhoneticsService(
                tmp_path / "phonetic_cache.json",
                tmp_path / "audio_cache",
                api_key="test-key",
                tts_model="gemini-2.5-flash-preview-tts",
                tts_voice="Kore",
            )

            with patch("dictionary_app.tts.post_generate_content", return_value=payload) as mocked_post:
                service.generate_audio(" biology ")

            post_payload = mocked_post.call_args.args[2]
            sent_text = post_payload["contents"][0]["parts"][0]["text"]
            self.assertEqual(sent_text, "biology")

    def test_generate_audio_falls_back_to_windows_on_gemini_runtime_error(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            service = PhoneticsService(
                tmp_path / "phonetic_cache.json",
                tmp_path / "audio_cache",
                api_key="test-key",
                tts_model="gemini-2.5-flash-preview-tts",
                tts_voice="Kore",
            )
            expected = service.audio_path("biology")

            with (
                patch("dictionary_app.tts.post_generate_content", side_effect=RuntimeError("HTTP 400 INVALID_ARGUMENT")),
                patch.object(service, "_windows_tts_available", return_value=True),
                patch.object(service, "_generate_audio_with_windows", return_value=expected) as mocked_windows,
            ):
                actual = service.generate_audio("biology")

            self.assertEqual(actual, expected)
            mocked_windows.assert_called_once_with("biology", expected)


if __name__ == "__main__":
    import unittest

    unittest.main()
