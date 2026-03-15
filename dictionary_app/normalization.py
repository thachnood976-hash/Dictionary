from __future__ import annotations

import re
import unicodedata

_EDGE_PUNCT_RE = re.compile(r"^[\W_]+|[\W_]+$")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?")


def normalize_word(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.strip().lower()
    normalized = _EDGE_PUNCT_RE.sub("", normalized)
    return normalized


def tokenize_text(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    return [normalize_word(token) for token in _TOKEN_RE.findall(normalized) if normalize_word(token)]
