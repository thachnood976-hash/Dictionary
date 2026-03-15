from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from .ai import GeminiExplainClient
from .analyzer import analyze_text
from .auto_define import auto_define_word, resolve_words_for_storage
from .benchmark import run_all_benchmarks, run_profile
from .config import DEFAULT_DATA_DIR
from .gui import main as gui_main
from .importers import fetch_url_text, import_vocabulary_file, load_text_file
from .online_lookup import OnlineDictionaryClient, format_entry_for_storage
from .sample_data import DEMO_ENTRIES
from .srs import ReviewStore
from .storage import DataFileError, DictionaryStore
from .tts import PhoneticsService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dictionary_app")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-demo")

    lookup_parser = subparsers.add_parser("lookup")
    lookup_parser.add_argument("word")

    prefix_parser = subparsers.add_parser("prefix")
    prefix_parser.add_argument("prefix")
    prefix_parser.add_argument("--method", choices=["trie", "bisect"], default="bisect")
    prefix_parser.add_argument("--limit", type=int, default=20)

    browse_parser = subparsers.add_parser("browse")
    browse_parser.add_argument("letter")
    browse_parser.add_argument("--limit", type=int, default=20)

    import_parser = subparsers.add_parser("import-vocab")
    import_parser.add_argument("path", type=Path)

    analyze_parser = subparsers.add_parser("analyze-text")
    source = analyze_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--file", type=Path)
    source.add_argument("--url")
    analyze_parser.add_argument("--limit", type=int, default=20)
    analyze_parser.add_argument("--schedule-tomorrow", nargs="*", default=[])

    due_parser = subparsers.add_parser("review-due")
    due_parser.add_argument("--answer-word")
    due_parser.add_argument("--result", choices=["remember", "forget"])

    ai_parser = subparsers.add_parser("ai-explain")
    ai_parser.add_argument("term")
    ai_parser.add_argument("--domain")

    online_parser = subparsers.add_parser("online-define")
    online_parser.add_argument("word")
    online_parser.add_argument("--save-local", action="store_true")

    ipa_parser = subparsers.add_parser("pronounce")
    ipa_parser.add_argument("word")
    ipa_parser.add_argument("--play", action="store_true")

    benchmark_parser = subparsers.add_parser("benchmark")
    benchmark_parser.add_argument("--lookup-sample-size", type=int, default=10_000)

    subparsers.add_parser("gui")
    subparsers.add_parser("profile")
    subparsers.add_parser("menu")
    return parser


def _load_store(data_dir: Path) -> DictionaryStore:
    store = DictionaryStore(data_dir)
    store.ensure_layout()
    store.load_if_available()
    return store


def _require_loaded(store: DictionaryStore) -> None:
    if not store.hash_index:
        raise DataFileError("Dictionary data is missing. Run `init-demo` or import vocabulary first.")


def _analysis_source(text: str | None, file_path: Path | None, url: str | None) -> str:
    if text is not None:
        return text
    if file_path is not None:
        return load_text_file(file_path)
    if url is not None:
        return fetch_url_text(url)
    raise ValueError("No input source provided.")


def _print_json(payload: object) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        sys.stdout.write(serialized + "\n")
    except UnicodeEncodeError:
        sys.stdout.buffer.write(serialized.encode("utf-8", errors="replace") + b"\n")


def run_command(args: argparse.Namespace) -> int:
    store = _load_store(args.data_dir)
    review_store = ReviewStore(store.paths.review_json)
    ai_client = GeminiExplainClient(store.paths.ai_cache_json)
    online_client = OnlineDictionaryClient(store.paths.online_cache_json)
    phonetics = PhoneticsService(store.paths.phonetic_cache_json, store.paths.audio_cache_dir)

    try:
        if args.command == "init-demo":
            store.build_from_mapping(DEMO_ENTRIES)
            print(f"Initialized demo dictionary in {args.data_dir}")
            return 0

        if args.command == "lookup":
            meaning = store.lookup(args.word) if store.hash_index else None
            source = "local"
            auto_saved = False
            if meaning is None:
                resolved = auto_define_word(store, online_client, args.word)
                meaning = resolved.meaning if resolved.usable else None
                source = "online" if meaning else "missing"
                auto_saved = resolved.saved
                if resolved.entry.phonetic:
                    phonetics.set_ipa(args.word, resolved.entry.phonetic)
            if meaning is None:
                print("Word not found locally or online.")
                return 1
            ipa = phonetics.ensure_ipa(args.word)
            _print_json({"word": args.word, "ipa": ipa, "meaning": meaning, "source": source, "auto_saved": auto_saved})
            return 0

        if args.command == "prefix":
            _require_loaded(store)
            if args.method == "trie":
                results = store.prefix_trie(args.prefix, args.limit)
            else:
                results = store.prefix_bisect(args.prefix, args.limit)
            _print_json(results)
            return 0

        if args.command == "browse":
            _require_loaded(store)
            _print_json(store.browse_letter(args.letter, args.limit))
            return 0

        if args.command == "import-vocab":
            result = import_vocabulary_file(args.path)
            resolved_items, resolution_results = resolve_words_for_storage(online_client, result.missing_words)
            for item in resolution_results:
                if item.entry.phonetic:
                    phonetics.set_ipa(item.stored_word, item.entry.phonetic)
            import_items = dict(result.items)
            import_items.update(resolved_items)
            if not import_items:
                _print_json(
                    {
                        "rows": 0,
                        "rows_read": result.rows_read,
                        "duplicates_in_file": result.duplicates,
                        "missing_meanings": len(result.missing_words),
                        "auto_defined": 0,
                        "unresolved_words": [item.requested_word for item in resolution_results if not item.usable],
                    }
                )
                return 1
            if store.hash_index:
                stats = store.upsert_entries(import_items)
            else:
                store.build_from_mapping(import_items)
                stats = {"rows": len(import_items), "new_words": len(import_items), "duplicates": 0}
            stats["rows_read"] = result.rows_read
            stats["duplicates_in_file"] = result.duplicates
            stats["missing_meanings"] = len(result.missing_words)
            stats["auto_defined"] = len(resolved_items)
            stats["unresolved_words"] = [item.requested_word for item in resolution_results if not item.usable]
            _print_json(stats)
            return 0

        if args.command == "analyze-text":
            source_text = _analysis_source(args.text, args.file, args.url)
            analysis = analyze_text(source_text, known_words=set(store.all_words()), limit=args.limit)
            if args.schedule_tomorrow:
                review_store.schedule_tomorrow(args.schedule_tomorrow)
            _print_json(analysis.to_dict())
            return 0

        if args.command == "review-due":
            if args.answer_word and args.result:
                updated = review_store.record_result(args.answer_word, args.result == "remember")
                _print_json(asdict(updated))
                return 0
            due = [asdict(item) for item in review_store.due_items()]
            _print_json(due)
            return 0

        if args.command == "ai-explain":
            response = ai_client.explain(args.term, domain=args.domain)
            _print_json(response)
            return 0

        if args.command == "online-define":
            result = online_client.lookup(args.word)
            if args.save_local and result.fetched:
                meaning = format_entry_for_storage(result)
                if store.hash_index:
                    store.upsert_entries({args.word: meaning})
                else:
                    store.build_from_mapping({args.word: meaning})
            _print_json(result.to_dict())
            return 0

        if args.command == "pronounce":
            ipa = phonetics.ensure_ipa(args.word)
            audio_path = phonetics.generate_audio(args.word)
            if args.play:
                phonetics.play_audio(audio_path)
            _print_json({"word": args.word, "ipa": ipa, "audio": str(audio_path)})
            return 0

        if args.command == "benchmark":
            _require_loaded(store)
            payload = run_all_benchmarks(store, store.paths.benchmark_json, lookup_sample_size=args.lookup_sample_size)
            _print_json(payload)
            return 0

        if args.command == "gui":
            store.close()
            return gui_main()

        if args.command == "profile":
            _require_loaded(store)
            run_profile(store, store.paths.profile_txt)
            print(f"Wrote profile report to {store.paths.profile_txt}")
            return 0

        if args.command == "menu":
            return run_menu(store, review_store, ai_client, phonetics)
    finally:
        store.close()
    return 0


def run_menu(
    store: DictionaryStore,
    review_store: ReviewStore,
    ai_client: GeminiExplainClient,
    phonetics: PhoneticsService,
) -> int:
    actions = {
        "1": "Lookup word",
        "2": "Prefix suggestions",
        "3": "Browse alphabet",
        "4": "Import vocabulary file",
        "5": "Import and analyze text file",
        "6": "Import and analyze from URL",
        "7": "Review due words",
        "8": "AI explain word or phrase",
        "9": "Show IPA and generate audio",
        "10": "Benchmark and profiling",
        "0": "Exit",
    }
    while True:
        for key, label in actions.items():
            print(f"{key}. {label}")
        choice = input("Select an option: ").strip()
        if choice == "0":
            return 0
        if choice == "1":
            word = input("Word: ")
            online_client = OnlineDictionaryClient(store.paths.online_cache_json)
            meaning = store.lookup(word) if store.hash_index else None
            if meaning is None:
                resolved = auto_define_word(store, online_client, word)
                meaning = resolved.meaning if resolved.usable else None
                if resolved.entry.phonetic:
                    phonetics.set_ipa(word, resolved.entry.phonetic)
            print(meaning or "Word not found locally or online.")
        elif choice == "2":
            prefix = input("Prefix: ")
            method = input("Method (trie/bisect) [bisect]: ").strip() or "bisect"
            results = store.prefix_trie(prefix) if method == "trie" else store.prefix_bisect(prefix)
            print(results)
        elif choice == "3":
            letter = input("Letter: ")
            print(store.browse_letter(letter))
        elif choice == "4":
            path = Path(input("Vocabulary file path: ").strip())
            result = import_vocabulary_file(path)
            online_client = OnlineDictionaryClient(store.paths.online_cache_json)
            resolved_items, resolution_results = resolve_words_for_storage(online_client, result.missing_words)
            for item in resolution_results:
                if item.entry.phonetic:
                    phonetics.set_ipa(item.stored_word, item.entry.phonetic)
            items = dict(result.items)
            items.update(resolved_items)
            if not items:
                print({"rows": 0, "auto_defined": 0, "unresolved_words": [item.requested_word for item in resolution_results]})
            else:
                stats = store.upsert_entries(items) if store.hash_index else {"rows": len(items), "new_words": len(items), "duplicates": 0}
                if not store.hash_index:
                    store.build_from_mapping(items)
                stats["auto_defined"] = len(resolved_items)
                stats["unresolved_words"] = [item.requested_word for item in resolution_results if not item.usable]
                print(stats)
        elif choice == "5":
            path = Path(input("Text file path: ").strip())
            analysis = analyze_text(load_text_file(path), known_words=set(store.all_words()))
            print(json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2))
            selection = input("Add words to review tomorrow (comma-separated, blank to skip): ").strip()
            if selection:
                added = review_store.schedule_tomorrow([part.strip() for part in selection.split(",") if part.strip()])
                print(f"Scheduled {added} new item(s).")
        elif choice == "6":
            url = input("URL: ").strip()
            analysis = analyze_text(fetch_url_text(url), known_words=set(store.all_words()))
            print(json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2))
        elif choice == "7":
            due = review_store.due_items()
            if not due:
                print("No words due today.")
            for item in due:
                print(item.word)
                answer = input("Remember or Forget? [r/f]: ").strip().lower()
                result = review_store.record_result(item.word, remembered=answer == "r")
                print(result)
        elif choice == "8":
            term = input("Word or phrase: ").strip()
            domain = input("Domain (optional): ").strip() or None
            print(json.dumps(ai_client.explain(term, domain=domain), ensure_ascii=False, indent=2))
        elif choice == "9":
            word = input("Word: ").strip()
            ipa = phonetics.ensure_ipa(word)
            audio = phonetics.generate_audio(word)
            print({"ipa": ipa, "audio": str(audio)})
        elif choice == "10":
            payload = run_all_benchmarks(store, store.paths.benchmark_json)
            run_profile(store, store.paths.profile_txt)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("Invalid option.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run_command(args)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1
