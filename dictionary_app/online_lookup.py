from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .json_store import load_json, save_json
from .normalization import normalize_word


@dataclass(slots=True)
class OnlineDefinition:
    definition: str
    example: str = ""
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OnlineMeaning:
    part_of_speech: str
    definitions: list[OnlineDefinition] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OnlineDictionaryEntry:
    word: str
    phonetic: str = ""
    phonetics: list[str] = field(default_factory=list)
    meanings: list[OnlineMeaning] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    license_name: str = ""
    license_url: str = ""
    fetched: bool = False
    error: str = ""
    message: str = ""
    api_url: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "OnlineDictionaryEntry":
        meanings: list[OnlineMeaning] = []
        for meaning in payload.get("meanings", []):
            meaning_dict = dict(meaning)
            definitions = [
                OnlineDefinition(**dict(item))
                for item in meaning_dict.get("definitions", [])
            ]
            meanings.append(
                OnlineMeaning(
                    part_of_speech=str(meaning_dict.get("part_of_speech", "")),
                    definitions=definitions,
                    synonyms=list(meaning_dict.get("synonyms", [])),
                    antonyms=list(meaning_dict.get("antonyms", [])),
                )
            )
        return cls(
            word=str(payload.get("word", "")),
            phonetic=str(payload.get("phonetic", "")),
            phonetics=list(payload.get("phonetics", [])),
            meanings=meanings,
            source_urls=list(payload.get("source_urls", [])),
            license_name=str(payload.get("license_name", "")),
            license_url=str(payload.get("license_url", "")),
            fetched=bool(payload.get("fetched", False)),
            error=str(payload.get("error", "")),
            message=str(payload.get("message", "")),
            api_url=str(payload.get("api_url", "")),
        )


class OnlineDictionaryClient:
    def __init__(self, cache_path: Path, language: str = "en", base_url: str | None = None) -> None:
        self.cache_path = cache_path
        self.language = language
        self.base_url = (base_url or os.getenv("ONLINE_DICTIONARY_BASE_URL") or "https://api.dictionaryapi.dev/api/v2/entries").rstrip("/")
        self.cache: dict[str, dict[str, object]] = load_json(cache_path, {})

    def lookup(self, word: str, force_refresh: bool = False) -> OnlineDictionaryEntry:
        normalized = normalize_word(word)
        if not normalized:
            raise ValueError("Word is required for online lookup.")

        cache_key = f"{self.language}:{normalized}"
        if not force_refresh and cache_key in self.cache:
            return OnlineDictionaryEntry.from_dict(dict(self.cache[cache_key]))

        entry = self.fetch(normalized)
        if entry.fetched:
            self.cache[cache_key] = entry.to_dict()
            save_json(self.cache_path, self.cache)
        return entry

    def fetch(self, word: str) -> OnlineDictionaryEntry:
        api_url = self.build_api_url(word)
        request = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "DictionaryApp2/0.1",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404:
                return parse_dictionary_api_payload(word, api_url, body, fetched=False, error="not_found")
            raise RuntimeError(f"Online dictionary lookup failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            return OnlineDictionaryEntry(
                word=word,
                fetched=False,
                error=str(exc.reason),
                message=f"Online dictionary lookup failed: {exc.reason}",
                api_url=api_url,
            )
        return parse_dictionary_api_payload(word, api_url, payload, fetched=True)

    def build_api_url(self, word: str) -> str:
        return build_api_url(word, language=self.language, base_url=self.base_url)

    def open_source(self, entry: OnlineDictionaryEntry) -> str:
        target = entry.source_urls[0] if entry.source_urls else entry.api_url
        if not target:
            raise RuntimeError("No source URL available for this entry.")
        webbrowser.open(target)
        return target


def parse_dictionary_api_payload(word: str, api_url: str, payload: str, fetched: bool, error: str = "") -> OnlineDictionaryEntry:
    import json

    data = json.loads(payload)

    if isinstance(data, dict):
        return OnlineDictionaryEntry(
            word=word,
            fetched=False,
            error=error or str(data.get("title", "")).lower().replace(" ", "_") or "lookup_failed",
            message=str(data.get("message", "")),
            api_url=api_url,
        )

    if not data:
        return OnlineDictionaryEntry(
            word=word,
            fetched=False,
            error="empty_response",
            message="Online dictionary returned no entries.",
            api_url=api_url,
        )

    raw_entry = dict(data[0])
    phonetics = _collect_phonetics(raw_entry)
    meanings: list[OnlineMeaning] = []
    for raw_meaning in raw_entry.get("meanings", []):
        meaning_dict = dict(raw_meaning)
        definitions = [
            OnlineDefinition(
                definition=str(item.get("definition", "")),
                example=str(item.get("example", "")),
                synonyms=list(item.get("synonyms", [])),
                antonyms=list(item.get("antonyms", [])),
            )
            for item in meaning_dict.get("definitions", [])
            if str(item.get("definition", "")).strip()
        ]
        meanings.append(
            OnlineMeaning(
                part_of_speech=str(meaning_dict.get("partOfSpeech", "")),
                definitions=definitions,
                synonyms=list(meaning_dict.get("synonyms", [])),
                antonyms=list(meaning_dict.get("antonyms", [])),
            )
        )

    license_info = dict(raw_entry.get("license", {}))
    entry = OnlineDictionaryEntry(
        word=str(raw_entry.get("word", word)),
        phonetic=str(raw_entry.get("phonetic", "")),
        phonetics=phonetics,
        meanings=meanings,
        source_urls=list(raw_entry.get("sourceUrls", [])),
        license_name=str(license_info.get("name", "")),
        license_url=str(license_info.get("url", "")),
        fetched=fetched,
        api_url=api_url,
    )
    if not entry.phonetic and entry.phonetics:
        entry.phonetic = entry.phonetics[0]
    return entry


def format_entry_for_storage(entry: OnlineDictionaryEntry) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    fallback: list[str] = []
    for meaning in entry.meanings:
        for item in meaning.definitions:
            definition = " ".join(item.definition.split())
            if not definition:
                continue
            lowered = definition.lower()
            if definition not in fallback:
                fallback.append(definition)
            if "usage notes" in lowered or lowered.startswith("(see "):
                continue
            if definition in seen:
                continue
            seen.add(definition)
            lines.append(definition)
            if len(lines) == 3:
                return "\n".join(lines).strip()
    if not lines:
        lines = fallback[:3]
    return "\n".join(lines).strip()


def _collect_phonetics(raw_entry: dict[str, object]) -> list[str]:
    results: list[str] = []
    for item in raw_entry.get("phonetics", []):
        text = str(dict(item).get("text", "")).strip()
        if text and text not in results:
            results.append(text)
    return results


def build_api_url(word: str, language: str = "en", base_url: str = "https://api.dictionaryapi.dev/api/v2/entries") -> str:
    encoded_word = urllib.parse.quote(word.strip())
    encoded_language = urllib.parse.quote(language)
    return f"{base_url.rstrip('/')}/{encoded_language}/{encoded_word}"
