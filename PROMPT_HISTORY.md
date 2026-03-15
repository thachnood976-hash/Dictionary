# 📝 Prompt History — LexiCore Dictionary App

Tài liệu này ghi lại toàn bộ các prompt đã sử dụng để xây dựng và phát triển ứng dụng từ điển LexiCore, bao gồm phân tích chi tiết những thay đổi mà mỗi prompt tạo ra.

---

## Phần A — Prompt gốc (Tạo khung ứng dụng)

> ⚠️ Các prompt dưới đây được **suy ra từ phân tích code**, không phải prompt chính xác. Ứng dụng ban đầu được tạo bằng AI tool trước khi đưa vào Antigravity.

---

### 🔧 Giai đoạn 1: Nền tảng dữ liệu

#### Prompt 1 — Cấu trúc project
> "Tạo ứng dụng từ điển Python dạng package `dictionary_app/` với file cấu hình, entry point `app.py`, và hỗ trợ `python -m dictionary_app`."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `config.py` | 69 | `AppPaths` dataclass — quản lý tất cả đường dẫn dữ liệu |
| `__init__.py` | ~5 | Package init |
| `__main__.py` | ~5 | `python -m` entry point |
| `app.py` | 2 | Entry point chính |

---

#### Prompt 2 — Chuẩn hoá từ
> "Tạo module chuẩn hoá từ: Unicode NFKC normalize, lowercase, loại bỏ dấu câu, tokenize văn bản."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `normalization.py` | 20 | `normalize_word()` + `tokenize_text()` |

**Chi tiết kỹ thuật:**
- Dùng `unicodedata.normalize("NFKC", ...)` cho Unicode
- Regex `_EDGE_PUNCT_RE` loại bỏ punctuation đầu/cuối
- Regex `_TOKEN_RE` tách từ (bao gồm cả dấu `'` và `-`)

---

#### Prompt 3 — Lưu trữ từ điển với mmap
> "Tạo `DictionaryStore` lưu trữ từ/nghĩa bằng file nhị phân + hash index, hỗ trợ O(1) lookup, mmap, browsing theo chữ cái, prefix search."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `storage.py` | 170 | `DictionaryStore` — core storage engine |
| `json_store.py` | ~20 | Helper `load_json()` / `save_json()` |

**Chi tiết thay đổi:**
- `meaning.data` — file nhị phân chứa nghĩa
- `index.data` — file text: `word\toffset\tlength` 
- Memory-mapped file (`mmap`) để đọc nghĩa O(1)
- `browse_letter()` dùng `bisect_left/right`
- `prefix_bisect()` + `prefix_trie()` cho tìm kiếm prefix
- `upsert_entries()` để thêm/cập nhật từ
- `build_from_mapping()` rebuild toàn bộ

---

#### Prompt 4 — Trie prefix tree
> "Tạo cấu trúc dữ liệu Trie cho tìm kiếm prefix nhanh."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `trie.py` | 48 | `Trie` class với DFS |

**Chi tiết:**
- `TrieNode` dataclass với `children` dict và `is_end` flag
- `insert()` — O(k) insert
- `starts_with(prefix, limit)` — DFS để tìm tất cả từ có prefix
- `from_words()` class method

---

#### Prompt 5 — Dữ liệu mẫu
> "Tạo bộ dữ liệu từ điển mẫu để demo."

**Files tạo ra:**
| File | Mô tả |
|------|-------|
| `sample_data.py` | `DEMO_ENTRIES` dict chứa các từ tiếng Anh mẫu kèm nghĩa |

---

### 🚀 Giai đoạn 2: Tính năng nâng cao

#### Prompt 6 — Nhập dữ liệu từ file/URL
> "Tạo module import từ vựng từ CSV, TSV, JSONL, plain text, và URL."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `importers.py` | 171 | Import engine đa định dạng |

**Chi tiết:**
- CSV/TSV với pandas fallback
- JSONL parser
- Plain text (tab-separated hoặc word-per-line)
- `fetch_url_text()` — HTTP fetch + HTML parser (`PlainTextExtractor`)
- `ImportResult`: items, missing_words, rows_read, duplicates

---

#### Prompt 7 — Phân tích văn bản
> "Tạo module phân tích tần suất từ, bigrams, và phân loại known/unknown."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `analyzer.py` | 66 | `analyze_text()` với stopwords filtering |

**Chi tiết:**
- `Counter` đếm tần suất từ
- Bigram extraction
- Phân loại `known`/`unknown` dựa trên từ điển
- 21 stopwords mặc định (a, an, the, is, ...)

---

#### Prompt 8 — Spaced Repetition System (SRS)
> "Tạo hệ thống ôn tập lặp lại ngắt quãng theo thuật toán SM-2."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `srs.py` | 142 | `ReviewStore` với SM-2 algorithm |

**Chi tiết thuật toán:**
- `ReviewItem`: word, next_review_date, interval_days, ease_factor, wrong/right count
- **Nhớ đúng:** `interval *= ease_factor`, `ease_factor += 0.1`
- **Nhớ sai:** `interval = 1`, `ease_factor -= 0.2` (min 1.3)
- `schedule_tomorrow()` — lên lịch ôn ngày mai
- `due_items()` — lọc từ đến hạn, có cache
- Migration: merge duplicate items, coerce dates

---

#### Prompt 9 — Flashcards
> "Tạo hệ thống flashcard với front/back/note/tags."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `flashcards.py` | 112 | `FlashcardStore` CRUD |

**Chi tiết:**
- `Flashcard` dataclass: front, back, note, tags
- CRUD: `upsert()`, `delete()`, `get()`, `list_cards()`
- Tag deduplication (case-insensitive)
- JSON persistence (`flashcards.json`)

---

#### Prompt 10 — Tra từ điển online
> "Kết nối API dictionaryapi.dev để tra từ online, cache kết quả."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `online_lookup.py` | 242 | `OnlineDictionaryClient` |

**Chi tiết:**
- API: `https://api.dictionaryapi.dev/api/v2/entries/en/{word}`
- Parse: word, phonetic, IPA, meanings, definitions, examples, synonyms, antonyms
- Cache trong `online_cache.json`
- `format_entry_for_storage()` — chuyển entry thành text đọc được
- `open_source()` — mở link Wiktionary trong browser

---

#### Prompt 11 — Auto-define từ online
> "Kết hợp online lookup và storage để tự động tra và lưu từ mới."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `auto_define.py` | 57 | `auto_define_word()` |

**Logic:**
1. Tra từ online → `resolve_online_meaning()`
2. Format nghĩa → `format_entry_for_storage()`
3. Lưu vào local dictionary → `store.upsert_entries()`

---

### 🤖 Giai đoạn 3: AI và phát âm

#### Prompt 12 — Gemini API wrapper
> "Tạo wrapper cho Google Gemini REST API."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `gemini_api.py` | 56 | API helper functions |

**Chi tiết:**
- `resolve_gemini_api_key()` từ `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY`
- `post_generate_content()` — POST request đến Gemini
- Models: `gemini-2.5-flash` (text), `gemini-2.5-flash-preview-tts` (audio)
- Voice: `Kore`

---

#### Prompt 13 — AI giải thích từ vựng
> "Tạo AI client giải thích từ, gợi ý cách dùng, và chatbot hỗ trợ học."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `ai.py` | 99 | `GeminiExplainClient` |

**3 chức năng AI:**
| Method | Output JSON keys | Mục đích |
|--------|-----------------|----------|
| `explain()` | core_meaning, academic_meaning, contexts, examples, mistakes | Giải thích chi tiết |
| `usage_hint()` | when_to_use, tone, common_situations, example | Gợi ý cách dùng |
| `assistant_reply()` | (text) | Chatbot trả lời câu hỏi |

- Cache kết quả trong `ai_cache.json`
- Sanitize input: loại bỏ email và số điện thoại

---

#### Prompt 14 — Text-to-Speech
> "Tạo dịch vụ phát âm: Gemini TTS hoặc Windows SpeechSynthesizer."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `tts.py` | 182 | `PhoneticsService` |

**Pipeline phát âm:**
```
Word → Gemini TTS API (PCM audio) → WAV file → winsound.PlaySound()
                ↓ (fallback)
     Windows SpeechSynthesizer (PowerShell)
```
- IPA cache trong `phonetic_cache.json`
- Audio files trong `audio_cache/`
- Cross-platform: winsound (Win), `open` (Mac), `xdg-open` (Linux)

---

### 🖥️ Giai đoạn 4: Giao diện

#### Prompt 15 — CLI
> "Tạo giao diện command-line với argparse."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `cli.py` | 361 | CLI + interactive menu |

**13 lệnh CLI:**
`init-demo`, `import`, `analyze`, `lookup`, `prefix`, `browse`, `review`, `benchmark`, `online-define`, `phonetics`, `explain`, `gui`, `menu`

---

#### Prompt 16 — Benchmark
> "Tạo module đo hiệu suất lookup và prefix search."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `benchmark.py` | 74 | Benchmark + profiling |

**Metrics:**
- `benchmark_lookup()` — 10,000 random lookups, đo avg_ms
- `benchmark_prefix()` — so sánh Trie vs bisect
- `run_profile()` — cProfile top 20 functions

---

#### Prompt 17 — GUI (tkinter)
> "Tạo giao diện đồ hoạ đầy đủ với tkinter."

**Files tạo ra:**
| File | Dòng | Mô tả |
|------|------|-------|
| `gui.py` | ~3,000+ | `DictionaryAppGUI` class |

**7 trang:**
| Trang | Chức năng |
|-------|-----------|
| Home | Search bar, Word of the Day |
| Lookup | Tra từ, nghĩa, IPA, audio |
| Saved Words | Danh sách SRS, ôn tập |
| Flashcards | Thẻ ghi nhớ front/back |
| Quiz | Trắc nghiệm từ vựng |
| Assistant | Chatbot AI |
| Performance | Benchmark results |

**Sidebar:** Navigation pills, branding, status card
**Theme system:** Nhiều bảng màu, scale font

---

#### Prompt 18 — Unit Tests
> "Tạo bộ unit tests cho tất cả module."

**Files tạo ra:** 11 file test
| File | Module test |
|------|------------|
| `test_storage_and_analysis.py` | storage + analyzer |
| `test_trie.py` | trie |
| `test_srs.py` | srs |
| `test_flashcards.py` | flashcards |
| `test_online_lookup.py` | online_lookup |
| `test_auto_define.py` | auto_define |
| `test_gui.py` | gui |
| `test_benchmark.py` | benchmark |
| `test_tts.py` | tts |
| `test_normalization.py` | normalization |
| `test_spellcheck.py` | spellcheck logic |

---

## Phần B — Prompt thay đổi (Antigravity)

> Các prompt dưới đây là những yêu cầu thay đổi đã thực hiện qua Antigravity, với phân tích chi tiết.

---

### Prompt 19 — Restyle giao diện LexiCore Glassmorphism
> "Redesign toàn bộ app với dark glassmorphism theme"

**Files thay đổi:** `gui.py`

| Thay đổi | Chi tiết |
|----------|---------|
| Theme mới `lexicore` | Background `#0b0e1a`, surface `#151a2e`, accent `#7c5cfc` |
| Background glows | Canvas vẽ 4 soft glow circles (purple, blue, pink, cyan) |
| Sidebar mới | Brand "✦ LexiCore", nav pills với purple highlight |
| Home page | Welcome greeting, pill search bar, Word of the Day |
| Typography | Georgia → Segoe UI |
| Default theme | cambridge → lexicore |
| Window title | "Dictionary App 2.0" → "LexiCore — AI Dictionary" |

---

### Prompt 20 — Redesign Home page (ChatGPT-style)
> "Thay Home page thành layout centered giống ChatGPT"

**Files thay đổi:** `gui.py` — `_build_home_page()`

| Trước | Sau |
|-------|-----|
| Dense search shell + hero section | Centered container tại `rely=0.43` |
| Nhiều elements | Chỉ welcome text + search bar |
| Placeholder tĩnh | Placeholder behavior (focus in/out) |

---

### Prompt 21 — Thêm Autocomplete trên Home
> "Hiển thị gợi ý autocomplete khi gõ"

**Files thay đổi:** `gui.py`

**Thêm mới:**
- `_home_suggest_listbox` — dropdown gợi ý
- `_home_on_key()` — lắng nghe KeyRelease
- `_home_show_suggestions()` / `_home_hide_suggestions()`
- `_home_suggest_select()` — chọn gợi ý
- `_home_suggest_down()` / `_home_suggest_up()` — điều hướng bàn phím

---

### Prompt 22 — Tích hợp Lookup vào Home
> "Hiển thị nghĩa, Vietnamese, audio trực tiếp trên Home"

**Files thay đổi:** `gui.py` — `_build_home_page()`

**Thêm mới:**
- `_home_results` panel với header, audio buttons, meaning columns
- `_home_meaning_output` — English meaning text panel
- `_home_vn_output` — Vietnamese meaning text panel
- `_home_do_lookup()` — lookup logic ngay trên Home
- `_home_show_results()` — hiển thị kết quả

---

### Prompt 23 — Online Vietnamese Translation (MyMemory API)
> "Tự động dịch từ sang tiếng Việt qua MyMemory API"

**Files tạo mới:**
| File | Dòng | Mô tả |
|------|------|-------|
| `translation_api.py` | ~50 | `TranslationClient` class |

**Files thay đổi:**
| File | Thay đổi |
|------|---------|
| `config.py` | Thêm `translation_cache_json` property |
| `gui.py` | Import `TranslationClient`, tạo instance trong `__init__` |
| `gui.py` | `_get_vietnamese_meaning_from_database()` gọi API khi không có local meaning |

**Flow:** Word → check local → **call MyMemory API** → cache `translation_cache.json`

---

### Prompt 24 — Bug Fixes (2 test failures)
> "Sửa labels tiếng Việt và thêm diacritic prefix variants"

**Files thay đổi:** `gui.py`

| Bug | Fix |
|-----|-----|
| `_format_hint_for_display()` dùng labels tiếng Anh | Đổi sang "Khi dùng", "Sắc thái", v.v. |
| `_extract_vietnamese_lines()` thiếu prefix dấu | Thêm `nghĩa:`, `tiếng việt:`, `dịch:` |

**Kết quả:** 24/24 tests pass (trước đó 22/24)

---

### Prompt 25 — Quiz Game enhancements
> "Thêm timer 2 phút, auto-advance, nút Previous"

**Files thay đổi:** `gui.py` — quiz page

| Tính năng | Chi tiết |
|-----------|---------|
| Timer 2 phút | Đếm ngược, tự kết thúc khi hết giờ |
| Auto-advance | Sau khi chọn đáp án, tự chuyển câu tiếp |
| Previous button | Quay lại câu trước |

---

### Prompt 26 — Redesign Review page
> "Restyle Review page giống layout Flashcard"

**Files thay đổi:** `gui.py` — `_build_review_page()`, `_render_review_from_word()`

| Trước | Sau |
|-------|-----|
| Text panel đơn giản | Card-based layout |
| `review_output` ScrolledText | Separate sections: meaning, Vietnamese, usage, schedule |
| review_text string | `review_meaning_var`, `review_vietnamese_var`, `review_usage_var`, `review_schedule_var` |

---

### Prompt 27 — Online Autocomplete (Datamuse API)
> "Thêm gợi ý autocomplete online từ Datamuse API"

**Files thay đổi:** `gui.py`

| Thay đổi | Chi tiết |
|----------|---------|
| `_suggest_timer` | Debounce 300ms trước khi fetch |
| `_suggest_cache` | Cache kết quả theo typed text |
| `_home_fetch_suggestions()` | Local matches trước → online sau |
| Background thread | `threading.Thread` gọi Datamuse API |
| `urllib.parse` import | Cho URL encoding |

**API:** `https://api.datamuse.com/sug?s={word}&max=8`
**Merge:** Local (top 4) + Online (top 8) → deduplicate → max 8 kết quả

---

### Prompt 28 — Đổi màu theme
> "Đồng bộ màu flashcard và saved word trong theme default"

**Files thay đổi:** `gui.py` — `_configure_theme()`

Đồng bộ `flash_colors` giữa flashcard page và saved words page trong theme `lexicore`.

---

### Prompt 29 — Liquid Background Animation
> "Thêm hiệu ứng nền liquid/fluid animation"

**Files thay đổi:** `gui.py`

Cập nhật `_draw_bg_glows()` và `_draw_glow_circle()` với hiệu ứng animated, mượt hơn.

---

### Prompt 30 — Performance Optimization
> "Tối ưu hiệu suất — fix lag"

**Files thay đổi:** `gui.py`, `storage.py`, `srs.py`

| Optimization | Impact | File |
|-------------|--------|------|
| Background-thread online lookup | 🔴 Eliminates 1-5s freezes | `gui.py` |
| Background-thread Vietnamese translation | 🔴 Eliminates 1-10s freezes | `gui.py` |
| Trie-based autocomplete | 🟡 O(prefix) vs O(n) | `gui.py` |
| Debounced canvas glows (150ms) | 🟡 Fewer redraws | `gui.py` |
| Cached audio count | 🟢 Avoids slow I/O | `gui.py` |
| Deferred post-lookup refreshes | 🟡 Faster perceived response | `gui.py` |
| Non-copying `all_words()` | 🟢 Avoids list copy | `storage.py` |
| Cached `due_items()` | 🟢 Avoids repeated filter+sort | `srs.py` |

---

### Prompt 31 — Package thành .exe
> "Đóng gói app thành file .exe bằng PyInstaller với icon tuỳ chỉnh"

**Files tạo mới:**
| File | Mô tả |
|------|-------|
| `DictionaryApp.spec` | PyInstaller spec file |
| `dictionary_app/assets/app_icon.ico` | Custom book icon |
| `dictionary_app/assets/app_icon.png` | PNG version |

**Output:** `dist/DictionaryApp/DictionaryApp.exe`

---

### Prompt 32 — Chia sẻ .exe
> "Hướng dẫn gửi file .exe cho người khác"

Không thay đổi code — chỉ hướng dẫn cách chia sẻ thư mục `dist/DictionaryApp/`.

---

## Tổng hợp

| Giai đoạn | Số prompt | Mô tả |
|-----------|-----------|-------|
| A. Tạo khung (trước Antigravity) | 18 | Từ nền tảng dữ liệu đến GUI hoàn chỉnh |
| B. Thay đổi (Antigravity) | 14 | UI redesign, tính năng mới, bug fixes, optimization |
| **Tổng cộng** | **~32 prompt** | **~9,000+ dòng code, 20 module, 11 file test** |

### Biểu đồ thay đổi theo file

```
gui.py          ████████████████████████████ (14 prompt thay đổi) — 3,176 dòng
storage.py      ██ (2 prompt) — 170 dòng  
srs.py          ██ (2 prompt) — 142 dòng
config.py       ██ (2 prompt) — 69 dòng
translation_api.py █ (1 prompt, mới) — ~50 dòng
Các module khác    █ (chỉ tạo ban đầu)
```
