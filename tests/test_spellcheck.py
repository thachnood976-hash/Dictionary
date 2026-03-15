import unittest

from dictionary_app.gui import DictionaryAppGUI


class SpellcheckTests(unittest.TestCase):
    def test_analyze_sentence_corrections_flags_i_was_pattern(self) -> None:
        vocab = {"i", "am", "a", "boy", "was"}
        issues, corrected = DictionaryAppGUI._analyze_sentence_corrections("i was a boy", vocab, sorted(vocab))
        replacements = {(issue["original"], issue["suggestion"]) for issue in issues}
        self.assertIn(("i", "I"), replacements)
        self.assertIn(("was", "am"), replacements)
        self.assertEqual(corrected, "I am a boy")

    def test_analyze_sentence_corrections_returns_clean_sentence(self) -> None:
        vocab = {"i", "am", "a", "boy"}
        issues, corrected = DictionaryAppGUI._analyze_sentence_corrections("I am a boy", vocab, sorted(vocab))
        self.assertEqual(issues, [])
        self.assertEqual(corrected, "I am a boy")


if __name__ == "__main__":
    unittest.main()
