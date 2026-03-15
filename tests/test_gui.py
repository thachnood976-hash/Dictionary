import unittest

from dictionary_app.gui import DictionaryAppGUI


class GuiHintFormattingTests(unittest.TestCase):
    def test_format_hint_handles_none_values(self) -> None:
        payload = {
            "when_to_use": None,
            "tone": "  Friendly  ",
            "common_situations": None,
            "example": "Hi there.",
        }

        formatted = DictionaryAppGUI._format_hint_for_display(None, payload)

        self.assertIn("Sắc thái: Friendly", formatted)
        self.assertIn("Ví dụ: Hi there.", formatted)
        self.assertNotIn("Khi dùng:", formatted)
        self.assertNotIn("Tình huống thường gặp:", formatted)

    def test_uppercase_first_character_for_flashcard_word(self) -> None:
        self.assertEqual(DictionaryAppGUI._uppercase_first_character("biology"), "Biology")
        self.assertEqual(DictionaryAppGUI._uppercase_first_character("crew locker"), "Crew locker")
        self.assertEqual(DictionaryAppGUI._uppercase_first_character(""), "")

    def test_extract_vietnamese_lines_only(self) -> None:
        payload = "\n".join(
            [
                "definition: the scientific study of living organisms.",
                "vi: ngành sinh học nghiên cứu sinh vật sống.",
                "source: local",
                "Nghĩa: khoa học về sự sống.",
                "Example: This is an example sentence.",
            ]
        )

        lines = DictionaryAppGUI._extract_vietnamese_lines(payload)

        self.assertIn("ngành sinh học nghiên cứu sinh vật sống.", lines)
        self.assertIn("khoa học về sự sống.", lines)
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
