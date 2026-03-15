from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_TEXT_MODEL = "gemini-2.5-flash"
DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_TTS_VOICE = "Kore"


def resolve_gemini_api_key(explicit: str | None = None) -> str | None:
    return explicit or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def resolve_text_model(explicit: str | None = None) -> str:
    return explicit or os.getenv("GEMINI_MODEL") or DEFAULT_TEXT_MODEL


def resolve_tts_model(explicit: str | None = None) -> str:
    return explicit or os.getenv("GEMINI_TTS_MODEL") or DEFAULT_TTS_MODEL


def resolve_tts_voice(explicit: str | None = None) -> str:
    return explicit or os.getenv("GEMINI_TTS_VOICE") or DEFAULT_TTS_VOICE


def build_generate_content_url(model: str) -> str:
    return (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urllib.parse.quote(model)}:generateContent"
    )


def post_generate_content(api_key: str, model: str, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    request = urllib.request.Request(
        build_generate_content_url(model),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini request failed: HTTP {exc.code} {detail}".strip()) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini request failed: {exc.reason}") from exc
