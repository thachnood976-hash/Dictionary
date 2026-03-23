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

    # --- Grammar correction via AI ---
    def grammar_correct(self, sentence: str) -> dict[str, str]:
        """Use Gemini to correct grammar and suggest improvements."""
        if not self.enabled:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY to enable AI grammar check.")
        sanitized = PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", sentence))
        prompt = (
            "You are an expert English grammar teacher. Analyze the following sentence and return strict JSON with keys:\n"
            "- corrected: the corrected sentence following formal English grammar\n"
            "- issues: a list of objects, each with 'original', 'correction', and 'explanation'\n"
            "- formal_version: rewrite the sentence in a formal, polished way\n"
            "- tips: a short grammar tip related to the mistakes found\n\n"
            f"Sentence: \"{sanitized}\""
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        payload = post_generate_content(self.api_key, self.model, body, timeout=30)
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

    # --- Translation ---
    def translate_text(self, text: str, target_lang: str = "auto") -> str:
        """Translate text between English and Vietnamese (auto-detect direction)."""
        if not self.enabled:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY to enable translation.")
        sanitized = PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", text))
        if target_lang == "auto":
            direction_hint = (
                "Auto-detect the language. If the text is in English, translate to Vietnamese. "
                "If the text is in Vietnamese, translate to English. "
                "If the text is in another language, translate to English."
            )
        elif target_lang == "vi":
            direction_hint = "Translate the text to Vietnamese."
        else:
            direction_hint = "Translate the text to English."
        prompt = (
            f"You are a professional translator. {direction_hint}\n"
            "Provide an accurate, natural-sounding translation. "
            "Keep the original meaning and tone. "
            "If the text contains idioms or expressions, translate them appropriately.\n\n"
            f"Text to translate:\n\"{sanitized}\""
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        payload = post_generate_content(self.api_key, self.model, body, timeout=30)
        return payload["candidates"][0]["content"]["parts"][0]["text"].strip()

    # --- Academic essay writing help ---
    def academic_essay_help(self, text: str, mode: str = "improve") -> str:
        """Help write or improve essays in academic English.

        *mode* is one of ``"outline"``, ``"write"``, ``"improve"``.
        """
        if not self.enabled:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY to enable essay help.")
        sanitized = PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", text))
        if mode == "outline":
            instruction = (
                "Create a detailed academic essay outline for the following topic. "
                "Include: thesis statement, 3-4 main body paragraphs with sub-points, "
                "introduction and conclusion notes. Use formal academic language."
            )
        elif mode == "write":
            instruction = (
                "Write a well-structured academic paragraph or short essay about the following topic. "
                "Use formal academic English with proper citations style (if applicable), "
                "transition words, and sophisticated vocabulary. "
                "The writing should be suitable for university-level coursework."
            )
        else:  # "improve"
            instruction = (
                "Improve the following text to make it more academic and formal. "
                "Fix grammar, enhance vocabulary, improve sentence structure, "
                "add transition words, and make it suitable for academic writing. "
                "Return the improved version followed by a brief explanation of the changes."
            )
        prompt = f"{instruction}\n\nText/Topic:\n\"{sanitized}\""
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3},
        }
        payload = post_generate_content(self.api_key, self.model, body, timeout=60)
        return payload["candidates"][0]["content"]["parts"][0]["text"].strip()

