from __future__ import annotations

import cProfile
import pstats
import random
import time
from pathlib import Path

from .json_store import save_json
from .storage import DictionaryStore


def benchmark_lookup(store: DictionaryStore, sample_size: int = 10_000) -> dict[str, float]:
    words = store.all_words()
    if not words:
        raise RuntimeError("Dictionary is empty.")
    queries = [random.choice(words) for _ in range(sample_size)]
    started = time.perf_counter()
    for word in queries:
        store.lookup(word)
    elapsed = time.perf_counter() - started
    return {
        "sample_size": sample_size,
        "total_seconds": elapsed,
        "avg_ms": (elapsed / sample_size) * 1000,
    }


def benchmark_prefix(store: DictionaryStore, prefixes: list[str], limit: int = 20) -> dict[str, dict[str, float]]:
    trie_started = time.perf_counter()
    for prefix in prefixes:
        store.prefix_trie(prefix, limit=limit)
    trie_elapsed = time.perf_counter() - trie_started

    bisect_started = time.perf_counter()
    for prefix in prefixes:
        store.prefix_bisect(prefix, limit=limit)
    bisect_elapsed = time.perf_counter() - bisect_started

    count = max(len(prefixes), 1)
    return {
        "trie": {"queries": len(prefixes), "avg_ms": (trie_elapsed / count) * 1000},
        "bisect": {"queries": len(prefixes), "avg_ms": (bisect_elapsed / count) * 1000},
    }


def run_profile(store: DictionaryStore, output_path: Path) -> None:
    profiler = cProfile.Profile()
    words = store.all_words()
    prefixes = [word[:3] for word in words[:100] if len(word) >= 3]
    profiler.enable()
    for word in words[:500]:
        store.lookup(word)
    for prefix in prefixes:
        store.prefix_trie(prefix)
        store.prefix_bisect(prefix)
    profiler.disable()

    stats = pstats.Stats(profiler).sort_stats("cumulative")
    with output_path.open("w", encoding="utf-8") as handle:
        stats.stream = handle
        stats.print_stats(20)


def run_all_benchmarks(store: DictionaryStore, output_path: Path, lookup_sample_size: int = 10_000) -> dict[str, object]:
    words = store.all_words()
    prefixes = sorted({word[:3] for word in words if len(word) >= 3})[:1000]
    payload = {
        "lookup": benchmark_lookup(store, sample_size=lookup_sample_size),
        "prefix": benchmark_prefix(store, prefixes or ["a"]),
    }
    save_json(output_path, payload)
    return payload
