import unittest

from dictionary_app.normalization import normalize_word, tokenize_text


class NormalizationTests(unittest.TestCase):
    def test_normalize_word(self) -> None:
        self.assertEqual(normalize_word("  Word!! "), "word")
        self.assertEqual(normalize_word("Ｂｉｏ"), "bio")

    def test_tokenize_text(self) -> None:
        self.assertEqual(tokenize_text("Bio-medical systems, and data."), ["bio-medical", "systems", "and", "data"])


if __name__ == "__main__":
    unittest.main()
