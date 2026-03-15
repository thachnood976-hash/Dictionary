from __future__ import annotations

import base64
import os
import platform
import subprocess
import wave
from pathlib import Path

from .gemini_api import post_generate_content, resolve_gemini_api_key, resolve_tts_model, resolve_tts_voice
from .json_store import load_json, save_json
from .normalization import normalize_word


class PhoneticsService:
    def __init__(
        self,
        cache_path: Path,
        audio_cache_dir: Path,
        api_key: str | None = None,
        tts_model: str | None = None,
        tts_voice: str | None = None,
    ) -> None:
        self.cache_path = cache_path
        self.audio_cache_dir = audio_cache_dir
        self.api_key = resolve_gemini_api_key(api_key)
        self.tts_model = resolve_tts_model(tts_model)
        self.tts_voice = resolve_tts_voice(tts_voice)
        self.cache = load_json(cache_path, {})
        self.audio_cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.api_key)

    def get_ipa(self, word: str) -> str | None:
        key = normalize_word(word)
        return self.cache.get(key)

    def set_ipa(self, word: str, ipa: str) -> None:
        key = normalize_word(word)
        if not key:
            return
        self.cache[key] = ipa
        save_json(self.cache_path, self.cache)

    def generate_audio(self, word: str) -> Path:
        transcript = word.strip()
        if not transcript:
            raise RuntimeError("Word is required for audio generation.")
        target = self.audio_path(transcript)
        if target.exists():
            return target
        if self.gemini_enabled:
            try:
                return self._generate_audio_with_gemini(transcript, target)
            except RuntimeError:
                if self._windows_tts_available():
                    return self._generate_audio_with_windows(transcript, target)
                raise
        if self._windows_tts_available():
            return self._generate_audio_with_windows(transcript, target)
        raise RuntimeError("Audio generation requires GEMINI_API_KEY/GOOGLE_API_KEY or Windows speech synthesis.")

    def audio_path(self, word: str) -> Path:
        target_name = normalize_word(word) or word.strip()
        return self.audio_cache_dir / f"{target_name}.wav"

    def has_audio(self, word: str) -> bool:
        return self.audio_path(word).exists()

    def provider_name(self) -> str:
        if self.gemini_enabled:
            return f"Gemini TTS ({self.tts_model})"
        if platform.system() == "Windows":
            return "Windows SpeechSynthesizer"
        return "No audio provider configured"

    def play_audio(self, path: Path) -> None:
        if platform.system() == "Windows":
            try:
                import winsound

                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            except ImportError:
                os.startfile(path)  # type: ignore[attr-defined]
                return
        if platform.system() == "Darwin":
            subprocess.Popen(["open", str(path)])
            return
        subprocess.Popen(["xdg-open", str(path)])

    def stop_audio(self) -> None:
        if platform.system() == "Windows":
            try:
                import winsound

                winsound.PlaySound(None, 0)
            except ImportError:
                return

    def ensure_ipa(self, word: str) -> str:
        ipa = self.get_ipa(word)
        if ipa:
            return ipa
        fallback = f"/{word}/"
        self.set_ipa(word, fallback)
        return fallback

    def _generate_audio_with_gemini(self, transcript: str, target: Path) -> Path:
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": transcript,
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": self.tts_voice,
                        }
                    }
                },
            },
        }
        response = post_generate_content(self.api_key or "", self.tts_model, payload, timeout=90)
        pcm_data = self._extract_pcm_audio(response)
        self._write_wav_file(target, pcm_data)
        return target

    def _windows_tts_available(self) -> bool:
        return platform.system() == "Windows"

    def _generate_audio_with_windows(self, transcript: str, target: Path) -> Path:
        escaped_target = str(target).replace("'", "''")
        escaped_word = transcript.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$speak.SetOutputToWaveFile('{escaped_target}');"
            f"$speak.Speak('{escaped_word}');"
            "$speak.Dispose();"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "Windows speech synthesis failed")
        return target

    def _extract_pcm_audio(self, payload: dict[str, object]) -> bytes:
        try:
            parts = payload["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Gemini audio response did not contain candidate audio data.") from exc
        for part in parts:
            inline_data = dict(part).get("inlineData")
            if not inline_data:
                continue
            encoded = dict(inline_data).get("data")
            if not encoded:
                continue
            return base64.b64decode(encoded)
        raise RuntimeError("Gemini audio response did not include inline audio data.")

    def _write_wav_file(self, target: Path, pcm_data: bytes) -> None:
        with wave.open(str(target), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(24000)
            handle.writeframes(pcm_data)
