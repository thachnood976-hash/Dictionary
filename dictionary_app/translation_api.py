from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .json_store import load_json, save_json
from .normalization import normalize_word


class TranslationClient:
    """Translate English words to Vietnamese using the free MyMemory API."""

    BASE_URL = "https://api.mymemory.translated.net/get"

    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        self.cache: dict[str, str] = load_json(cache_path, {})

    def translate(self, word: str, timeout: int = 10) -> str:
        key = normalize_word(word)
        if not key:
            return ""
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        try:
            result = self._fetch(key, timeout=timeout)
        except Exception:
            return ""

        self.cache[key] = result
        save_json(self.cache_path, self.cache)
        return result

    def translate_lines(self, lines: list[str], timeout: int = 10) -> str:
        """Translate each line individually and return them joined with newlines.

        This ensures the number of Vietnamese lines matches the English lines.
        """
        results: list[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            translated = self.translate(line, timeout=timeout)
            if translated:
                results.append(translated)
            else:
                # Keep original if translation fails
                results.append(line)
        return "\n".join(results)

    def _fetch(self, word: str, timeout: int = 10) -> str:
        params = urllib.parse.urlencode({"q": word, "langpair": "en|vi"})
        url = f"{self.BASE_URL}?{params}"
        request = urllib.request.Request(url, headers={"User-Agent": "DictionaryApp2/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError):
            return ""

        translated = payload.get("responseData", {}).get("translatedText", "")
        if not translated or translated.lower() == word.lower():
            return ""
        return translated.strip()
