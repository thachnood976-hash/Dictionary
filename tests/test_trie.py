import unittest

from dictionary_app.trie import Trie


class TrieTests(unittest.TestCase):
    def test_insert_and_prefix(self) -> None:
        trie = Trie.from_words(["bio", "biology", "biography", "cache"])
        self.assertEqual(trie.starts_with("bio", 3), ["bio", "biography", "biology"])
        self.assertEqual(trie.starts_with("ca"), ["cache"])


if __name__ == "__main__":
    unittest.main()
