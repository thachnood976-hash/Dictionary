# 📖 Dictionary App 2.0

A full-featured English–Vietnamese dictionary desktop application built with Python and Tkinter. It provides fast local lookup, AI-powered features, spaced repetition, flashcards, grammar checking, and text-to-speech — all in a modern, themeable GUI.

---

## ✨ Features

| Feature | Description |
|---|---|
| **O(1) Hash Lookup** | Instant word lookup using a memory-mapped hash index |
| **Trie Autocomplete** | Real-time prefix suggestions as you type, with online API fallback (Datamuse) |
| **Vietnamese Translation** | Auto-translated meanings with local cache |
| **AI Assistant** | Gemini-powered explanations, essay writing, grammar advice |
| **Flashcards Studio** | Create, shuffle, quiz, and match flashcards with SRS scheduling |
| **Spaced Repetition (SRS)** | SM-2 algorithm for review scheduling with "Due Today" tracking |
| **Grammar Checker** | Local rule-based grammar analysis with AI-enhanced checking |
| **Text-to-Speech** | IPA phonetics and audio pronunciation with caching |
| **Multi-Theme UI** | 4 built-in themes: Default (dark), Blue White, Black White, Black Gold |
| **Import/Export** | Import vocabulary from files, URLs, or clipboard |
| **Benchmarking** | Built-in profiling and performance measurement tools |

---

## 🚀 How to Run

### Prerequisites

- **Python 3.11+** installed
- Install dependencies:
  ```bash
  pip install google-generativeai gtts pygame
  ```

### Run the GUI (recommended)

```bash
python app.py
```

### Run the CLI

```bash
python -m dictionary_app --help          # Show all CLI commands
python -m dictionary_app gui             # Launch GUI from CLI
python -m dictionary_app init-demo       # Load demo entries
python -m dictionary_app lookup biology  # Look up a word
python -m dictionary_app menu            # Interactive CLI menu
```

### Run Tests

```bash
python -m unittest discover -s tests
```

### Run the Packaged .exe (no Python needed)

```
dist\DictionaryApp.exe
```

> **Note:** Place the `data/` folder in the same directory as the `.exe` so it can find the dictionary database.

---

## 📁 Project Structure

```
Dictionary/
├── app.py                      # GUI entry point
├── DictionaryApp.spec           # PyInstaller packaging config
├── README.md                    # This file
├── data/                        # Dictionary database (auto-created)
│   ├── index.data               # Hash index: word → offset + length
│   ├── meaning.data             # Meanings stored as raw bytes
│   ├── alphabet.idx             # Sorted word list for bisect search
│   ├── trie.idx                 # Trie data for prefix autocomplete
│   ├── review.json              # SRS review schedule
│   ├── flashcards.json          # Custom flashcard decks
│   ├── ai_cache.json            # Cached AI responses
│   ├── online_cache.json        # Cached online API lookups
│   ├── phonetic_cache.json      # IPA and phonetics cache
│   ├── translation_cache.json   # Vietnamese translation cache
│   ├── ui_settings.json         # Theme and font preferences
│   └── audio_cache/             # Generated pronunciation audio files
├── dictionary_app/              # Main application package
│   ├── __init__.py              # Package init (version: 0.1.0)
│   ├── __main__.py              # CLI entry point
│   ├── gui.py                   # Full GUI application (Tkinter)
│   ├── cli.py                   # Command-line interface
│   ├── storage.py               # Hash index + mmap-based data store
│   ├── config.py                # Path configuration (AppPaths)
│   ├── trie.py                  # Trie data structure for suggestions
│   ├── normalization.py         # Word normalization utilities
│   ├── srs.py                   # Spaced Repetition System (SM-2)
│   ├── flashcards.py            # Flashcard data model + store
│   ├── grammar.py               # Rule-based grammar checker
│   ├── ai.py                    # Gemini AI client for explanations
│   ├── gemini_api.py            # Low-level Gemini API wrapper
│   ├── online_lookup.py         # Online dictionary API client
│   ├── translation_api.py       # Vietnamese translation service
│   ├── tts.py                   # Text-to-speech & phonetics
│   ├── benchmark.py             # Performance benchmarking
│   ├── analyzer.py              # Text analysis utilities
│   ├── auto_define.py           # Auto-define unknown words
│   ├── importers.py             # Vocabulary import from files/URLs
│   ├── sample_data.py           # Demo dictionary entries
│   ├── json_store.py            # JSON file read/write helpers
│   └── assets/                  # App icons
│       ├── app_icon.png
│       └── app_icon.ico
└── tests/                       # Unit tests
    └── test_spellcheck.py
```

---

## ⚙️ How the Code Works

### 1. Application Startup

```
app.py → imports gui.main() → creates DictionaryAppGUI → Tkinter mainloop
```

- `app.py` is the entry point. It imports `main()` from `dictionary_app/gui.py` and runs it.
- `DictionaryAppGUI.__init__()` initializes all services (storage, AI, TTS, SRS, flashcards, translation), loads UI settings, configures the theme, builds the layout, and starts the Tkinter event loop.

### 2. Data Storage Engine (`storage.py`)

The dictionary uses a **custom binary storage format** for performance:

- **`index.data`** — Tab-separated file mapping each word to its byte offset and length in `meaning.data`
- **`meaning.data`** — Raw UTF-8 encoded meanings, read via **memory-mapped I/O** (`mmap`) for O(1) random access
- **`alphabet.idx`** — Sorted word list enabling bisect-based prefix search
- **`trie.idx`** — JSON-serialized trie for real-time autocomplete suggestions

**Lookup flow:**
```
User types word → normalize_word() → hash_index[word] → mmap read at offset → return meaning
```

### 3. GUI Architecture (`gui.py`)

The GUI is a **single-window, multi-page** Tkinter application:

| Page | Purpose |
|---|---|
| **Home** | Search bar with autocomplete, quick word lookup |
| **Search** | Detailed lookup with English + Vietnamese meanings |
| **Review** | SRS-based daily word review |
| **Flashcards** | Interactive flashcard studio with quiz/match modes |
| **Grammar** | Rule-based + AI grammar checking |
| **AI Assistant** | Ask questions, translate, write essays |
| **Benchmark** | Performance profiling |

**Theme System:**
- 4 themes defined in `_configure_theme()`: `default`, `blue white`, `black_white`, `black_gold`
- Colors are stored in `self.colors` dict and applied to all widgets
- Button text color auto-adjusts (black/white) based on background luminance

### 4. Autocomplete (`gui.py` + `trie.py`)

```
Keypress → local trie search (instant) → show suggestions
         → debounce 400ms → fetch Datamuse API (background thread) → merge + update
```

- Local trie results appear instantly; online results merge in seamlessly.
- Results are cached in `_suggest_cache` to avoid redundant API calls.

### 5. Spaced Repetition (`srs.py`)

Uses the **SM-2 algorithm**:
- Words are scheduled for review based on performance (Remember / Again)
- `ReviewStore` tracks due dates, intervals, and ease factors
- The Review page shows all words due today

### 6. Flashcards (`flashcards.py`)

- Supports three modes: **Due Today**, **All Words**, **Custom Cards**
- Features: create, edit, delete, shuffle, quiz mode, match mode
- Click zones: left third = previous, center = reveal, right third = next

### 7. Grammar Checker (`grammar.py`)

- **Rule-based engine** checking: capitalization, double negatives, subject-verb agreement, common confusables, punctuation
- **AI-enhanced mode** sends text to Gemini for advanced corrections

### 8. AI Integration (`ai.py` + `gemini_api.py`)

- Uses **Google Gemini API** for word explanations, essay writing, translation, and grammar
- Responses are cached in `ai_cache.json` to minimize API calls
- Features: Ask Assistant, Translate, Essay Improve/Outline/Write

### 9. Text-to-Speech (`tts.py`)

- Generates pronunciation audio using **gTTS** (Google Text-to-Speech)
- Plays audio via **pygame**
- Caches IPA data and audio files locally

---

## 📦 Packaging as .exe

To build the standalone executable:

```bash
pip install pyinstaller
pyinstaller DictionaryApp.spec --noconfirm
```

The output will be at `dist/DictionaryApp.exe`. To share it:
1. Copy `DictionaryApp.exe` from the `dist/` folder
2. Place your `data/` folder in the same directory as the `.exe`
3. Run `DictionaryApp.exe` — no Python installation needed!

---

## 🎨 Themes

| Theme | Style |
|---|---|
| **Default** | Dark purple with animated glow background |
| **Blue White** | Light professional blue and white |
| **Black White** | Deep navy blue |
| **Black Gold** | Elegant dark with gold accents |

Change themes from the settings within the app. Preferences are saved in `data/ui_settings.json`.

---

## 📝 License

This project is for educational purposes.
