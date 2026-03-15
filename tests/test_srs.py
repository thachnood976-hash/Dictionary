import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from dictionary_app.json_store import save_json
from dictionary_app.srs import ReviewStore


class ReviewStoreTests(unittest.TestCase):
    def test_schedule_and_review(self) -> None:
        with TemporaryDirectory() as tmp:
            store = ReviewStore(Path(tmp) / "review.json")
            added = store.schedule_tomorrow(["biology"], today=date(2026, 3, 2))
            self.assertEqual(added, 1)
            due = store.due_items(today=date(2026, 3, 3))
            self.assertEqual([item.word for item in due], ["biology"])
            updated = store.record_result("biology", remembered=True, today=date(2026, 3, 3))
            self.assertEqual(updated.last_result, "remember")
            self.assertEqual(updated.right_count, 1)

    def test_load_normalizes_existing_review_items(self) -> None:
        with TemporaryDirectory() as tmp:
            review_path = Path(tmp) / "review.json"
            save_json(
                review_path,
                {
                    "items": [
                        {
                            "word": " Biology ",
                            "next_review_date": "2026-03-03",
                            "interval_days": 1,
                            "ease_factor": 2.5,
                            "wrong_count": 0,
                            "right_count": 1,
                            "last_result": "remember",
                        },
                        {
                            "word": "biology",
                            "next_review_date": "bad-date",
                            "interval_days": 2,
                            "ease_factor": 2.1,
                            "wrong_count": 1,
                            "right_count": 0,
                            "last_result": "forget",
                        },
                    ]
                },
            )

            store = ReviewStore(review_path)

            self.assertEqual(list(store.items), ["biology"])
            self.assertGreaterEqual(store.items["biology"].wrong_count, 1)
            self.assertEqual(store.record_result("Biology", remembered=False, today=date(2026, 3, 3)).word, "biology")


if __name__ == "__main__":
    unittest.main()
