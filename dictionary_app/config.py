from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppPaths:
    root: Path

    @property
    def index_data(self) -> Path:
        return self.root / "index.data"

    @property
    def meaning_data(self) -> Path:
        return self.root / "meaning.data"

    @property
    def alphabet_index(self) -> Path:
        return self.root / "alphabet.idx"

    @property
    def trie_index(self) -> Path:
        return self.root / "trie.idx"

    @property
    def review_json(self) -> Path:
        return self.root / "review.json"

    @property
    def ai_cache_json(self) -> Path:
        return self.root / "ai_cache.json"

    @property
    def online_cache_json(self) -> Path:
        return self.root / "online_cache.json"

    @property
    def phonetic_cache_json(self) -> Path:
        return self.root / "phonetic_cache.json"

    @property
    def audio_cache_dir(self) -> Path:
        return self.root / "audio_cache"

    @property
    def benchmark_json(self) -> Path:
        return self.root / "bench.json"

    @property
    def profile_txt(self) -> Path:
        return self.root / "profile.txt"

    @property
    def ui_settings_json(self) -> Path:
        return self.root / "ui_settings.json"

    @property
    def flashcards_json(self) -> Path:
        return self.root / "flashcards.json"

    @property
    def translation_cache_json(self) -> Path:
        return self.root / "translation_cache.json"


def _resolve_app_dir() -> Path:
    """Return the root directory of the app (works for both Python and frozen .exe)."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller .exe — use the directory containing the .exe
        return Path(sys.executable).resolve().parent
    # Normal Python execution — use the project root (parent of dictionary_app/)
    return Path(__file__).resolve().parent.parent


DEFAULT_DATA_DIR = _resolve_app_dir() / "data"
