from __future__ import annotations

import csv
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from .normalization import normalize_word


class PlainTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.chunks.append(data.strip())

    def text(self) -> str:
        return " ".join(self.chunks)


@dataclass(slots=True)
class ImportResult:
    items: dict[str, str]
    missing_words: list[str]
    rows_read: int
    duplicates: int


def _optional_pandas_rows(path: Path, delimiter: str | None) -> list[dict[str, str]] | None:
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        return None

    frame = pd.read_csv(path, sep=delimiter or ",", dtype=str).dropna(how="all").fillna("")
    frame.columns = [str(col).strip().lower() for col in frame.columns]
    return frame.to_dict(orient="records")


def import_vocabulary_file(path: Path) -> ImportResult:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return _import_jsonl(path)
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        return _import_delimited(path, delimiter)
    if suffix == ".txt":
        return _import_plain_vocab(path)
    raise ValueError(f"Unsupported vocabulary file type: {suffix}")


def _import_delimited(path: Path, delimiter: str) -> ImportResult:
    rows = _optional_pandas_rows(path, delimiter)
    if rows is None:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            rows = [dict(row) for row in reader]

    items: dict[str, str] = {}
    missing_words: list[str] = []
    seen_words: set[str] = set()
    duplicates = 0
    for row in rows:
        word = normalize_word(row.get("word", ""))
        meaning = str(row.get("meaning", "")).strip()
        if not word:
            continue
        if word in seen_words:
            duplicates += 1
        seen_words.add(word)
        if meaning:
            items[word] = meaning
            if word in missing_words:
                missing_words.remove(word)
        elif word not in missing_words:
            missing_words.append(word)
    return ImportResult(items=items, missing_words=missing_words, rows_read=len(rows), duplicates=duplicates)


def _import_jsonl(path: Path) -> ImportResult:
    items: dict[str, str] = {}
    missing_words: list[str] = []
    rows_read = 0
    seen_words: set[str] = set()
    duplicates = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows_read += 1
            row = json.loads(line)
            word = normalize_word(str(row.get("word", "")))
            meaning = str(row.get("meaning", "")).strip()
            if not word:
                continue
            if word in seen_words:
                duplicates += 1
            seen_words.add(word)
            if meaning:
                items[word] = meaning
                if word in missing_words:
                    missing_words.remove(word)
            elif word not in missing_words:
                missing_words.append(word)
    return ImportResult(items=items, missing_words=missing_words, rows_read=rows_read, duplicates=duplicates)


def _import_plain_vocab(path: Path) -> ImportResult:
    items: dict[str, str] = {}
    missing_words: list[str] = []
    rows_read = 0
    seen_words: set[str] = set()
    duplicates = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows_read += 1
            if "\t" in line:
                raw_word, raw_meaning = line.split("\t", 1)
                word = normalize_word(raw_word)
                meaning = raw_meaning.strip()
            else:
                word = normalize_word(line)
                meaning = ""
            if not word:
                continue
            if word in seen_words:
                duplicates += 1
            seen_words.add(word)
            if meaning:
                items[word] = meaning
                if word in missing_words:
                    missing_words.remove(word)
            elif word not in missing_words:
                missing_words.append(word)
    return ImportResult(items=items, missing_words=missing_words, rows_read=rows_read, duplicates=duplicates)


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fetch_url_text(url: str, timeout: int = 10) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must start with http:// or https://")

    request = urllib.request.Request(url, headers={"User-Agent": "DictionaryApp2/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            payload = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP error {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc

    if "html" in content_type.lower():
        parser = PlainTextExtractor()
        parser.feed(payload)
        return parser.text()
    return payload
