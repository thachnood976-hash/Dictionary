# Dictionary App 2.0

Local dictionary CLI with:

- `O(1)` hash-based lookup
- alphabet browsing and bisect prefix search
- Trie prefix suggestions
- vocabulary/text import from files or URLs
- text analysis and next-day review scheduling
- spaced repetition review
- optional AI explanation
- online dictionary API lookup with definitions, examples, phonetics, and source links
- IPA cache and pronunciation audio generation
- benchmarking and profiling

## Quick start

```bash
python app.py
python -m dictionary_app --help
python -m dictionary_app gui
python -m dictionary_app init-demo
python -m dictionary_app lookup biology
python -m dictionary_app online-define biology
python -m dictionary_app prefix bio --method trie
python -m dictionary_app menu
python -m unittest discover -s tests
```

## Data layout

The default data directory is `./data`.

- `index.data`
- `meaning.data`
- `alphabet.idx`
- `trie.idx`
- `review.json`
- `ai_cache.json`
- `online_cache.json`
- `phonetic_cache.json`
- `audio_cache/`
