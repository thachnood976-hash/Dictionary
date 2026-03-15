import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dictionary_app.benchmark import run_all_benchmarks
from dictionary_app.storage import DictionaryStore


class BenchmarkTests(unittest.TestCase):
    def test_run_all_benchmarks_with_real_store(self) -> None:
        with TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            store = DictionaryStore(data_dir)
            store.ensure_layout()
            store.build_from_mapping(
                {
                    "biology": "The study of life",
                    "biography": "A life story",
                    "algorithm": "A set of steps to solve a problem",
                }
            )

            payload = run_all_benchmarks(store, store.paths.benchmark_json, lookup_sample_size=50)

            self.assertIn("lookup", payload)
            self.assertIn("prefix", payload)
            self.assertTrue(store.paths.benchmark_json.exists())
            store.close()


if __name__ == "__main__":
    unittest.main()
