from __future__ import annotations

from dataclasses import dataclass, field

from .online_lookup import OnlineDictionaryClient, OnlineDictionaryEntry, format_entry_for_storage
from .storage import DictionaryStore


@dataclass(slots=True)
class AutoDefineResult:
    requested_word: str
    stored_word: str
    meaning: str
    entry: OnlineDictionaryEntry
    saved: bool = False
    save_stats: dict[str, int] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return bool(self.meaning)


def resolve_online_meaning(client: OnlineDictionaryClient, word: str) -> AutoDefineResult:
    entry = client.lookup(word)
    stored_word = entry.word.strip() if entry.word.strip() else word.strip()
    meaning = format_entry_for_storage(entry) if entry.fetched else ""
    return AutoDefineResult(
        requested_word=word,
        stored_word=stored_word,
        meaning=meaning,
        entry=entry,
    )


def auto_define_word(store: DictionaryStore, client: OnlineDictionaryClient, word: str) -> AutoDefineResult:
    result = resolve_online_meaning(client, word)
    if not result.usable:
        return result
    if store.hash_index:
        result.save_stats = store.upsert_entries({result.stored_word: result.meaning})
    else:
        store.build_from_mapping({result.stored_word: result.meaning})
        result.save_stats = {"rows": 1, "new_words": 1, "duplicates": 0}
    result.saved = True
    return result


def resolve_words_for_storage(client: OnlineDictionaryClient, words: list[str]) -> tuple[dict[str, str], list[AutoDefineResult]]:
    resolved: dict[str, str] = {}
    results: list[AutoDefineResult] = []
    for word in words:
        result = resolve_online_meaning(client, word)
        results.append(result)
        if result.usable:
            resolved[result.stored_word] = result.meaning
    return resolved, results
