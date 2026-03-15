from __future__ import annotations

import io
import logging
import mmap
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from pathlib import Path

from .config import AppPaths
from .json_store import load_json, save_json
from .normalization import normalize_word
from .trie import Trie

logger = logging.getLogger(__name__)


class DataFileError(RuntimeError):
    pass


@dataclass(slots=True)
class DictionaryRecord:
    offset: int
    length: int


class DictionaryStore:
    def __init__(self, data_dir: Path) -> None:
        self.paths = AppPaths(data_dir)
        self.data_dir = data_dir
        self.hash_index: dict[str, DictionaryRecord] = {}
        self.alphabet_index: list[str] = []
        self.trie: Trie | None = None
        self._meaning_handle: io.BufferedReader | None = None
        self._meaning_mmap: mmap.mmap | None = None

    def ensure_layout(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.paths.audio_cache_dir.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        if self._meaning_mmap is not None:
            self._meaning_mmap.close()
            self._meaning_mmap = None
        if self._meaning_handle is not None:
            self._meaning_handle.close()
            self._meaning_handle = None

    def build_from_mapping(self, mapping: dict[str, str]) -> None:
        self.ensure_layout()
        self.close()
        normalized: dict[str, str] = {}
        for word, meaning in mapping.items():
            normalized_word = normalize_word(word)
            if normalized_word:
                normalized[normalized_word] = str(meaning).strip()
        if not normalized:
            raise ValueError("Cannot build dictionary from an empty mapping.")

        offset = 0
        with self.paths.meaning_data.open("wb") as meaning_handle, self.paths.index_data.open(
            "w", encoding="utf-8"
        ) as index_handle:
            for word in sorted(normalized):
                payload = normalized[word].encode("utf-8")
                meaning_handle.write(payload)
                index_handle.write(f"{word}\t{offset}\t{len(payload)}\n")
                offset += len(payload)

        words = sorted(normalized)
        self.paths.alphabet_index.write_text("\n".join(words), encoding="utf-8")
        save_json(self.paths.trie_index, {"words": words})
        logger.info("Built dictionary with %s entries", len(words))
        self.reload()

    def reload(self) -> None:
        self.close()
        self.hash_index = self._load_hash_index()
        self.alphabet_index = self._load_alphabet_index()
        self.trie = self._load_trie()
        self._open_mmap()

    def load_if_available(self) -> None:
        if self.paths.index_data.exists() and self.paths.meaning_data.exists():
            self.reload()

    def _load_hash_index(self) -> dict[str, DictionaryRecord]:
        if not self.paths.index_data.exists():
            raise DataFileError(f"Missing index file: {self.paths.index_data}")
        index: dict[str, DictionaryRecord] = {}
        with self.paths.index_data.open("r", encoding="utf-8") as handle:
            for line in handle:
                word, offset, length = line.rstrip("\n").split("\t")
                index[word] = DictionaryRecord(int(offset), int(length))
        logger.info("Loaded hash index with %s entries", len(index))
        return index

    def _load_alphabet_index(self) -> list[str]:
        if self.paths.alphabet_index.exists():
            words = [line.strip() for line in self.paths.alphabet_index.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            words = sorted(self.hash_index)
            self.paths.alphabet_index.write_text("\n".join(words), encoding="utf-8")
        return words

    def _load_trie(self) -> Trie:
        if self.paths.trie_index.exists():
            payload = load_json(self.paths.trie_index, {"words": []})
            words = payload.get("words", [])
        else:
            words = self.alphabet_index
            save_json(self.paths.trie_index, {"words": words})
        return Trie.from_words(words)

    def _open_mmap(self) -> None:
        if not self.paths.meaning_data.exists():
            raise DataFileError(f"Missing meaning file: {self.paths.meaning_data}")
        self._meaning_handle = self.paths.meaning_data.open("rb")
        self._meaning_mmap = mmap.mmap(self._meaning_handle.fileno(), length=0, access=mmap.ACCESS_READ)

    def lookup(self, word: str) -> str | None:
        normalized = normalize_word(word)
        record = self.hash_index.get(normalized)
        if record is None or self._meaning_mmap is None:
            return None
        payload = self._meaning_mmap[record.offset : record.offset + record.length]
        return payload.decode("utf-8")

    def browse_letter(self, letter: str, limit: int = 20) -> list[str]:
        normalized = normalize_word(letter)[:1]
        if not normalized:
            return []
        start = bisect_left(self.alphabet_index, normalized)
        end = bisect_right(self.alphabet_index, normalized + "{")
        return self.alphabet_index[start:end][:limit]

    def prefix_bisect(self, prefix: str, limit: int = 20) -> list[str]:
        normalized = normalize_word(prefix)
        start = bisect_left(self.alphabet_index, normalized)
        end = bisect_right(self.alphabet_index, normalized + "{")
        return self.alphabet_index[start:end][:limit]

    def prefix_trie(self, prefix: str, limit: int = 20) -> list[str]:
        normalized = normalize_word(prefix)
        if self.trie is None:
            return []
        return self.trie.starts_with(normalized, limit=limit)

    def upsert_entries(self, mapping: dict[str, str]) -> dict[str, int]:
        current = {word: self.lookup(word) or "" for word in self.alphabet_index}
        before = len(current)
        duplicates = 0
        for word, meaning in mapping.items():
            normalized = normalize_word(word)
            if not normalized:
                continue
            if normalized in current:
                duplicates += 1
            current[normalized] = meaning
        self.build_from_mapping(current)
        return {
            "rows": len(mapping),
            "new_words": max(len(current) - before, 0),
            "duplicates": duplicates,
        }

    def all_words(self) -> list[str]:
        return self.alphabet_index
