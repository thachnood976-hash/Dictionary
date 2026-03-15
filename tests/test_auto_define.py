import argparse
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from dictionary_app.auto_define import auto_define_word, resolve_words_for_storage
from dictionary_app.cli import run_command
from dictionary_app.online_lookup import OnlineDefinition, OnlineDictionaryEntry, OnlineMeaning
from dictionary_app.storage import DictionaryStore


def _sample_entry(word: str = "biology") -> OnlineDictionaryEntry:
    return OnlineDictionaryEntry(
        word=word,
        phonetic="/baɪˈɒl.ə.dʒi/",
        meanings=[
            OnlineMeaning(
                part_of_speech="noun",
                definitions=[
                    OnlineDefinition(
                        definition="The study of life and living organisms.",
                        example="Biology explains how cells function.",
                    )
                ],
            )
        ],
        source_urls=["https://en.wiktionary.org/wiki/biology"],
        fetched=True,
        api_url="https://api.dictionaryapi.dev/api/v2/entries/en/biology",
    )


class AutoDefineTests(unittest.TestCase):
    def test_auto_define_word_saves_into_empty_store(self) -> None:
        with TemporaryDirectory() as tmp:
            store = DictionaryStore(Path(tmp) / "data")
            store.ensure_layout()
            client = Mock()
            client.lookup.return_value = _sample_entry()

            result = auto_define_word(store, client, "biology")

            self.assertTrue(result.saved)
            self.assertTrue(result.usable)
            self.assertIn("study of life", store.lookup("biology") or "")
            store.close()

    def test_resolve_words_for_storage_collects_successes_and_failures(self) -> None:
        client = Mock()
        client.lookup.side_effect = [
            _sample_entry("biology"),
            OnlineDictionaryEntry(word="unknown", fetched=False, error="not_found"),
        ]

        resolved, results = resolve_words_for_storage(client, ["biology", "unknown"])

        self.assertIn("biology", resolved)
        self.assertEqual(len(results), 2)
        self.assertFalse(results[1].usable)

    def test_cli_lookup_uses_online_fallback_and_saves_result(self) -> None:
        with TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            args = argparse.Namespace(command="lookup", word="biology", data_dir=data_dir)

            with patch("dictionary_app.cli.OnlineDictionaryClient.lookup", return_value=_sample_entry()):
                with redirect_stdout(io.StringIO()):
                    exit_code = run_command(args)

            store = DictionaryStore(data_dir)
            store.ensure_layout()
            store.load_if_available()
            self.assertEqual(exit_code, 0)
            self.assertIn("study of life", store.lookup("biology") or "")
            store.close()


if __name__ == "__main__":
    unittest.main()
