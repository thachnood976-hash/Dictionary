import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dictionary_app.flashcards import FlashcardStore


class FlashcardStoreTests(unittest.TestCase):
    def test_upsert_and_reload(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "flashcards.json"
            store = FlashcardStore(path)
            store.upsert("  Biology  ", "Study of life", note="Core definition", tags=["science", " Science "])

            reloaded = FlashcardStore(path)
            card = reloaded.get("biology")
            self.assertIsNotNone(card)
            if card is None:
                self.fail("Expected flashcard to exist after reload.")
            self.assertEqual(card.front, "Biology")
            self.assertEqual(card.back, "Study of life")
            self.assertEqual(card.note, "Core definition")
            self.assertEqual(card.tags, ["science"])

    def test_delete_card(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "flashcards.json"
            store = FlashcardStore(path)
            store.upsert("biology", "Study of life")

            self.assertTrue(store.delete("biology"))
            self.assertFalse(store.delete("biology"))
            self.assertIsNone(store.get("biology"))


if __name__ == "__main__":
    unittest.main()
