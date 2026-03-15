from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .json_store import load_json, save_json
from .normalization import normalize_word


@dataclass(slots=True)
class ReviewItem:
    word: str
    next_review_date: str
    interval_days: int = 1
    ease_factor: float = 2.5
    wrong_count: int = 0
    right_count: int = 0
    last_result: str = "new"


class ReviewStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.items: dict[str, ReviewItem] = {}
        self._due_cache: list[ReviewItem] | None = None
        self.load()

    def load(self) -> None:
        payload = load_json(self.path, {"items": []})
        migrated = False
        normalized_items: dict[str, ReviewItem] = {}
        for item in payload.get("items", []):
            try:
                review_item = self._coerce_item(dict(item))
            except (TypeError, ValueError):
                migrated = True
                continue
            if review_item.word in normalized_items:
                normalized_items[review_item.word] = self._merge_items(normalized_items[review_item.word], review_item)
                migrated = True
            else:
                normalized_items[review_item.word] = review_item
            if review_item.word != str(item.get("word", "")):
                migrated = True
        self.items = normalized_items
        self._due_cache = None
        if migrated:
            self.save()

    def save(self) -> None:
        save_json(self.path, {"items": [asdict(item) for item in sorted(self.items.values(), key=lambda x: x.word)]})

    def schedule_tomorrow(self, words: list[str], today: date | None = None) -> int:
        current_day = today or datetime.now().astimezone().date()
        tomorrow = current_day + timedelta(days=1)
        added = 0
        for word in words:
            normalized = normalize_word(word)
            if not normalized:
                continue
            existing = self.items.get(normalized)
            if existing is None:
                self.items[normalized] = ReviewItem(word=normalized, next_review_date=tomorrow.isoformat())
                added += 1
            else:
                existing.next_review_date = tomorrow.isoformat()
        self._due_cache = None
        self.save()
        return added

    def due_items(self, today: date | None = None) -> list[ReviewItem]:
        current_day = today or datetime.now().astimezone().date()
        if self._due_cache is not None and today is None:
            return self._due_cache
        result = sorted(
            [item for item in self.items.values() if date.fromisoformat(item.next_review_date) <= current_day],
            key=lambda item: item.next_review_date,
        )
        if today is None:
            self._due_cache = result
        return result

    def record_result(self, word: str, remembered: bool, today: date | None = None) -> ReviewItem:
        current_day = today or datetime.now().astimezone().date()
        normalized = normalize_word(word)
        if not normalized:
            raise ValueError("Review word is required.")
        item = self.items.setdefault(normalized, ReviewItem(word=normalized, next_review_date=current_day.isoformat()))
        if remembered:
            item.right_count += 1
            item.last_result = "remember"
            item.interval_days = 1 if item.interval_days <= 1 else int(round(item.interval_days * item.ease_factor))
            item.ease_factor = max(1.3, item.ease_factor + 0.1)
        else:
            item.wrong_count += 1
            item.last_result = "forget"
            item.interval_days = 1
            item.ease_factor = max(1.3, item.ease_factor - 0.2)
        item.next_review_date = (current_day + timedelta(days=item.interval_days)).isoformat()
        self._due_cache = None
        self.save()
        return item

    def _coerce_item(self, payload: dict[str, object]) -> ReviewItem:
        word = normalize_word(str(payload.get("word", "")))
        if not word:
            raise ValueError("Invalid review word.")
        next_review_date = self._coerce_date(str(payload.get("next_review_date", "")))
        interval_days = max(int(payload.get("interval_days", 1) or 1), 1)
        ease_factor = max(float(payload.get("ease_factor", 2.5) or 2.5), 1.3)
        wrong_count = max(int(payload.get("wrong_count", 0) or 0), 0)
        right_count = max(int(payload.get("right_count", 0) or 0), 0)
        last_result = str(payload.get("last_result", "new") or "new")
        return ReviewItem(
            word=word,
            next_review_date=next_review_date,
            interval_days=interval_days,
            ease_factor=ease_factor,
            wrong_count=wrong_count,
            right_count=right_count,
            last_result=last_result,
        )

    def _coerce_date(self, raw_value: str) -> str:
        try:
            return date.fromisoformat(raw_value).isoformat()
        except ValueError:
            return datetime.now().astimezone().date().isoformat()

    def _merge_items(self, left: ReviewItem, right: ReviewItem) -> ReviewItem:
        next_review_date = min(left.next_review_date, right.next_review_date)
        return ReviewItem(
            word=left.word,
            next_review_date=next_review_date,
            interval_days=max(left.interval_days, right.interval_days),
            ease_factor=max(left.ease_factor, right.ease_factor),
            wrong_count=left.wrong_count + right.wrong_count,
            right_count=left.right_count + right.right_count,
            last_result=right.last_result if right.next_review_date >= left.next_review_date else left.last_result,
        )
