import unittest

from dictionary_app.grammar import analyze_grammar


class GrammarTests(unittest.TestCase):
    """Tests for the comprehensive grammar engine."""

    # --- Existing tests (backward-compat) ---

    def test_i_was_pattern(self) -> None:
        vocab = {"i", "am", "a", "boy", "was"}
        issues, corrected = analyze_grammar("i was a boy", vocab, sorted(vocab))
        replacements = {(issue["original"], issue["suggestion"]) for issue in issues}
        self.assertIn(("i", "I"), replacements)
        self.assertIn(("was", "am"), replacements)
        self.assertEqual(corrected, "I am a boy.")

    def test_clean_sentence(self) -> None:
        vocab = {"i", "am", "a", "boy"}
        issues, corrected = analyze_grammar("I am a boy.", vocab, sorted(vocab))
        # Only issues should be about missing punctuation if already correct
        self.assertEqual(corrected, "I am a boy.")

    # --- Capitalization ---

    def test_capitalize_first_word(self) -> None:
        _, corrected = analyze_grammar("hello world.", set(), [])
        self.assertTrue(corrected.startswith("Hello"))

    def test_pronoun_i_uppercase(self) -> None:
        issues, _ = analyze_grammar("i like cats.", set(), [])
        originals = {issue["original"] for issue in issues}
        self.assertIn("i", originals)

    # --- Subject-verb agreement ---

    def test_he_are(self) -> None:
        issues, corrected = analyze_grammar("He are happy.", set(), [])
        replacements = {(i["original"], i["suggestion"]) for i in issues}
        self.assertIn(("are", "is"), replacements)

    def test_they_is(self) -> None:
        issues, _ = analyze_grammar("They is here.", set(), [])
        replacements = {(i["original"], i["suggestion"]) for i in issues}
        self.assertIn(("is", "are"), replacements)

    def test_she_have(self) -> None:
        issues, _ = analyze_grammar("She have a cat.", set(), [])
        replacements = {(i["original"], i["suggestion"]) for i in issues}
        self.assertIn(("have", "has"), replacements)

    # --- Articles ---

    def test_a_before_vowel(self) -> None:
        issues, corrected = analyze_grammar("a apple.", set(), [])
        self.assertIn("an", corrected.lower())

    def test_an_before_consonant(self) -> None:
        issues, corrected = analyze_grammar("an dog.", set(), [])
        self.assertIn("a", corrected.lower())

    def test_a_before_university(self) -> None:
        # "university" starts with vowel letter but consonant sound
        _, corrected = analyze_grammar("an university.", set(), [])
        self.assertTrue(corrected.lower().startswith("a university"))

    def test_an_before_hour(self) -> None:
        _, corrected = analyze_grammar("a hour.", set(), [])
        self.assertIn("an", corrected.lower())

    # --- Confusables ---

    def test_your_before_adjective(self) -> None:
        issues, _ = analyze_grammar("your very smart.", set(), [])
        replacements = {(i["original"], i["suggestion"]) for i in issues}
        # First word gets capitalized, so suggestion is "You're"
        self.assertIn(("your", "You're"), replacements)

    def test_dont_missing_apostrophe(self) -> None:
        issues, _ = analyze_grammar("I dont know.", set(), [])
        replacements = {(i["original"], i["suggestion"]) for i in issues}
        self.assertIn(("dont", "don't"), replacements)

    # --- Double negatives ---

    def test_double_negative(self) -> None:
        issues, _ = analyze_grammar("I don't have no money.", set(), [])
        replacements = {(i["original"], i["suggestion"]) for i in issues}
        self.assertIn(("no", "any"), replacements)

    # --- Redundancy ---

    def test_very_unique(self) -> None:
        issues, _ = analyze_grammar("This is very unique.", set(), [])
        suggestions = {i["suggestion"] for i in issues}
        self.assertIn("unique", suggestions)

    # --- Punctuation ---

    def test_missing_period(self) -> None:
        issues, corrected = analyze_grammar("I like cats", set(), [])
        self.assertTrue(corrected.endswith("."))

    def test_no_false_period_for_question(self) -> None:
        issues, corrected = analyze_grammar("Do you like cats?", set(), [])
        self.assertFalse(corrected.endswith("?."))

    # --- Comparison: then/than ---

    def test_then_vs_than(self) -> None:
        issues, _ = analyze_grammar("She is better then me.", set(), [])
        replacements = {(i["original"], i["suggestion"]) for i in issues}
        self.assertIn(("then", "than"), replacements)


if __name__ == "__main__":
    unittest.main()
