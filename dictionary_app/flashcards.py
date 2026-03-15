from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from .json_store import load_json, save_json
from .normalization import normalize_word


@dataclass(slots=True)
class Flashcard:
    front: str
    back: str
    note: str = ""
    tags: list[str] = field(default_factory=list)


class FlashcardStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.cards: dict[str, Flashcard] = {}
        self.load()

    def load(self) -> None:
        payload = load_json(self.path, {"cards": []})
        cards: dict[str, Flashcard] = {}
        for item in payload.get("cards", []):
            try:
                front = self._clean_text(item.get("front", ""))
                back = self._clean_text(item.get("back", ""))
                if not front or not back:
                    continue
                card = Flashcard(
                    front=front,
                    back=back,
                    note=self._clean_text(item.get("note", "")),
                    tags=self._clean_tags(item.get("tags", [])),
                )
                cards[self._key(front)] = card
            except Exception:
                continue
        self.cards = cards

    def save(self) -> None:
        payload = {
            "cards": [asdict(card) for card in sorted(self.cards.values(), key=lambda card: card.front.lower())],
        }
        save_json(self.path, payload)

    def list_cards(self) -> list[Flashcard]:
        return sorted(self.cards.values(), key=lambda card: card.front.lower())

    def card_words(self) -> list[str]:
        return [card.front for card in self.list_cards()]

    def get(self, front: str) -> Flashcard | None:
        key = self._key(front)
        if not key:
            return None
        return self.cards.get(key)

    def upsert(self, front: str, back: str, note: str = "", tags: list[str] | None = None) -> Flashcard:
        cleaned_front = self._clean_text(front)
        cleaned_back = self._clean_text(back)
        if not cleaned_front:
            raise ValueError("Flashcard front is required.")
        if not cleaned_back:
            raise ValueError("Flashcard back is required.")
        card = Flashcard(
            front=cleaned_front,
            back=cleaned_back,
            note=self._clean_text(note),
            tags=self._clean_tags(tags or []),
        )
        self.cards[self._key(cleaned_front)] = card
        self.save()
        return card

    def delete(self, front: str) -> bool:
        key = self._key(front)
        if not key:
            return False
        removed = self.cards.pop(key, None)
        if removed is None:
            return False
        self.save()
        return True

    def _key(self, front: str) -> str:
        return normalize_word(front)

    def _clean_text(self, value: object) -> str:
        return " ".join(str(value or "").split()).strip()

    def _clean_tags(self, values: object) -> list[str]:
        if isinstance(values, str):
            parts = values.split(",")
        else:
            try:
                parts = list(values)  # type: ignore[arg-type]
            except TypeError:
                parts = []
        tags: list[str] = []
        seen: set[str] = set()
        for part in parts:
            cleaned = self._clean_text(part)
            normalized = cleaned.lower()
            if cleaned and normalized not in seen:
                tags.append(cleaned)
                seen.add(normalized)
        return tags
