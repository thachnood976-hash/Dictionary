import unittest

from dictionary_app.online_lookup import build_api_url, format_entry_for_storage, parse_dictionary_api_payload


class OnlineLookupTests(unittest.TestCase):
    def test_build_api_url(self) -> None:
        url = build_api_url("biology")
        self.assertEqual(url, "https://api.dictionaryapi.dev/api/v2/entries/en/biology")

    def test_parse_dictionary_api_payload(self) -> None:
        payload = """
        [
          {
            "word": "biology",
            "phonetic": "/baɪˈɒl.ə.dʒi/",
            "phonetics": [
              {"text": "/baɪˈɒl.ə.dʒi/"}
            ],
            "meanings": [
              {
                "partOfSpeech": "noun",
                "definitions": [
                  {
                    "definition": "The study of life and living organisms.",
                    "example": "Biology explains how cells function.",
                    "synonyms": ["life science"]
                  }
                ]
              }
            ],
            "sourceUrls": ["https://en.wiktionary.org/wiki/biology"]
          }
        ]
        """
        result = parse_dictionary_api_payload("biology", build_api_url("biology"), payload, fetched=True)
        self.assertTrue(result.fetched)
        self.assertEqual(result.word, "biology")
        self.assertEqual(result.phonetic, "/baɪˈɒl.ə.dʒi/")
        self.assertEqual(result.meanings[0].part_of_speech, "noun")
        self.assertIn("living organisms", result.meanings[0].definitions[0].definition)

    def test_format_entry_for_storage(self) -> None:
        payload = """
        [
          {
            "word": "biology",
            "phonetic": "/baɪˈɒl.ə.dʒi/",
            "meanings": [
              {
                "partOfSpeech": "noun",
                "definitions": [
                  {
                    "definition": "(see usage notes)"
                  },
                  {
                    "definition": "The study of life and living organisms.",
                    "example": "Biology explains how cells function."
                  }
                ]
              }
            ],
            "sourceUrls": ["https://en.wiktionary.org/wiki/biology"]
          }
        ]
        """
        result = parse_dictionary_api_payload("biology", build_api_url("biology"), payload, fetched=True)
        formatted = format_entry_for_storage(result)
        self.assertIn("The study of life and living organisms.", formatted)
        self.assertNotIn("usage notes", formatted.lower())
        self.assertNotIn("IPA:", formatted)
        self.assertNotIn("Example:", formatted)
        self.assertNotIn("Source:", formatted)


if __name__ == "__main__":
    unittest.main()
