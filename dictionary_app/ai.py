from __future__ import annotations

import json
import re
from pathlib import Path

from .gemini_api import post_generate_content, resolve_gemini_api_key, resolve_text_model
from .json_store import load_json, save_json

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d[\d -]{7,}\d)\b")


class GeminiExplainClient:
    def __init__(self, cache_path: Path, api_key: str | None = None, model: str | None = None) -> None:
        self.cache_path = cache_path
        self.api_key = resolve_gemini_api_key(api_key)
        self.model = resolve_text_model(model)
        self.cache = load_json(cache_path, {})

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def explain(self, term: str, domain: str | None = None, lang: str = "en") -> dict[str, str]:
        key = "|".join([term.strip().lower(), domain or "", lang])
        if key in self.cache:
            return self.cache[key]
        if not self.enabled:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY to enable AI explain.")

        sanitized = PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", term))
        prompt = (
            "Explain this dictionary entry in strict JSON with keys "
            "core_meaning, academic_meaning, contexts, examples, mistakes. "
            f"Term: {sanitized}. Domain: {domain or 'general'}. Language: {lang}."
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        payload = post_generate_content(self.api_key, self.model, body, timeout=30)
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        self.cache[key] = parsed
        save_json(self.cache_path, self.cache)
        return parsed

    def usage_hint(self, term: str, meaning: str = "", lang: str = "en") -> dict[str, str]:
        key = f"usage|{term.strip().lower()}|{lang}"
        if key in self.cache:
            return self.cache[key]
        if not self.enabled:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY to enable usage hints.")

        sanitized_term = PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", term))
        sanitized_meaning = PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", meaning))
        prompt = (
            "You are helping an English learner. Return strict JSON with keys "
            "when_to_use, tone, common_situations, example. "
            f"Word: {sanitized_term}. Meaning: {sanitized_meaning or 'not provided'}. "
            "Explain briefly when this word is appropriate in real communication."
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
        }
        payload = post_generate_content(self.api_key, self.model, body, timeout=30)
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        self.cache[key] = parsed
        save_json(self.cache_path, self.cache)
        return parsed

    def assistant_reply(self, question: str, word: str = "", meaning: str = "") -> str:
        if not self.enabled:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY to enable AI assistant.")
        sanitized_question = PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", question))
        sanitized_word = PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", word))
        sanitized_meaning = PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", meaning))
        context_lines = []
        if sanitized_word:
            context_lines.append(f"Current word: {sanitized_word}")
        if sanitized_meaning:
            context_lines.append(f"Saved meaning: {sanitized_meaning}")
        context = "\n".join(context_lines) or "No dictionary entry context."
        prompt = (
            "You are a concise English-learning assistant. Answer the user's question in the same language "
            "the user used, give practical advice, and keep the answer focused.\n"
            f"{context}\n"
            f"User question: {sanitized_question}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4},
        }
        payload = post_generate_content(self.api_key, self.model, body, timeout=30)
        return payload["candidates"][0]["content"]["parts"][0]["text"].strip()
