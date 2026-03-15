from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

from .normalization import tokenize_text

DEFAULT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}


@dataclass(slots=True)
class AnalysisItem:
    word: str
    frequency: int
    status: str


@dataclass(slots=True)
class TextAnalysis:
    items: list[AnalysisItem]
    bigrams: list[tuple[str, int]]
    total_tokens: int

    def to_dict(self) -> dict[str, object]:
        return {
            "items": [asdict(item) for item in self.items],
            "bigrams": [{"bigram": key, "count": value} for key, value in self.bigrams],
            "total_tokens": self.total_tokens,
        }


def analyze_text(text: str, known_words: set[str], limit: int = 20, stopwords: set[str] | None = None) -> TextAnalysis:
    active_stopwords = stopwords or DEFAULT_STOPWORDS
    tokens = [token for token in tokenize_text(text) if token and token not in active_stopwords]
    counts = Counter(tokens)
    bigram_counts = Counter(" ".join(pair) for pair in zip(tokens, tokens[1:]))
    items = [
        AnalysisItem(word=word, frequency=count, status="known" if word in known_words else "unknown")
        for word, count in counts.most_common(limit)
    ]
    return TextAnalysis(items=items, bigrams=bigram_counts.most_common(limit), total_tokens=len(tokens))
