import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dictionary_app.analyzer import analyze_text
from dictionary_app.importers import import_vocabulary_file
from dictionary_app.storage import DictionaryStore


class StorageAndAnalysisTests(unittest.TestCase):
    def test_import_lookup_and_analysis(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "words.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["word", "meaning"])
                writer.writeheader()
                writer.writerow({"word": "biology", "meaning": "The study of life"})
                writer.writerow({"word": "biography", "meaning": "A life story"})

            store = DictionaryStore(tmp_path / "data")
            store.ensure_layout()
            store.build_from_mapping({"algorithm": "A procedure"})
            imported = import_vocabulary_file(csv_path)
            stats = store.upsert_entries(imported.items)
            self.assertEqual(stats["new_words"], 2)
            self.assertEqual(store.lookup("biology"), "The study of life")
            self.assertEqual(store.prefix_bisect("bio"), ["biography", "biology"])

            analysis = analyze_text("Biology and biography appear in this text.", known_words=set(store.all_words()))
            statuses = {item.word: item.status for item in analysis.items}
            self.assertEqual(statuses["biology"], "known")
            self.assertEqual(statuses["biography"], "known")
            store.close()

    def test_import_tracks_words_missing_meanings_for_auto_define(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            txt_path = tmp_path / "words.txt"
            txt_path.write_text("biology\nbiography\tA life story\n", encoding="utf-8")

            imported = import_vocabulary_file(txt_path)

            self.assertEqual(imported.items["biography"], "A life story")
            self.assertEqual(imported.missing_words, ["biology"])


if __name__ == "__main__":
    unittest.main()
