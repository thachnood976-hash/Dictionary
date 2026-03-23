# 📖 Giải Thích Tính Năng — Dictionary App 2.0

Tài liệu này mô tả chi tiết các tính năng, thuật toán, và cơ chế hoạt động của ứng dụng từ điển.

---

## 📋 Mục Lục

1. [Tra từ nhanh (Home)](#1-tra-từ-nhanh-home)
2. [Gợi ý tự động (Autocomplete)](#2-gợi-ý-tự-động-autocomplete)
3. [Tra cứu trực tuyến (Online Lookup)](#3-tra-cứu-trực-tuyến-online-lookup)
4. [Hệ thống ôn tập (Spaced Repetition)](#4-hệ-thống-ôn-tập-spaced-repetition)
5. [Flashcards (Thẻ ghi nhớ)](#5-flashcards-thẻ-ghi-nhớ)
6. [Kiểm tra ngữ pháp (Grammar Checker)](#6-kiểm-tra-ngữ-pháp-grammar-checker)
7. [Trợ lý AI (AI Assistant)](#7-trợ-lý-ai-ai-assistant)
8. [Phát âm (Text-to-Speech)](#8-phát-âm-text-to-speech)
9. [Giao diện & Theme](#9-giao-diện--theme)
10. [Nhập dữ liệu (Import)](#10-nhập-dữ-liệu-import)
11. [Kiến trúc lưu trữ](#11-kiến-trúc-lưu-trữ)
12. [Đóng gói ứng dụng](#12-đóng-gói-ứng-dụng)

---

## 1. Tra từ nhanh (Home)

### Tính năng
- Gõ từ vào thanh tìm kiếm → hiện nghĩa tiếng Anh và tiếng Việt cùng lúc
- Bấm ▶ Play để nghe phát âm
- Bấm ★ Save to Review để lưu từ vào danh sách ôn tập

### Thuật toán tra cứu — O(1) Hash Lookup
```
Người dùng gõ "hello"
    → normalize_word("hello") → "hello"
    → hash_index["hello"] → {offset: 1024, length: 85}
    → mmap đọc 85 bytes tại vị trí 1024
    → Trả về nghĩa tiếng Anh
```

- **Hash Index**: Dictionary Python (`dict`) ánh xạ từ → vị trí trong file. Tra cứu O(1).
- **Memory-Mapped I/O (mmap)**: File nghĩa từ được ánh xạ vào bộ nhớ, đọc trực tiếp bằng offset mà không cần mở file lại. Cực nhanh.

### File liên quan
| File | Vai trò |
|---|---|
| `storage.py` | Hash index + mmap lookup |
| `normalization.py` | Chuẩn hóa từ (lowercase, trim) |
| `data/index.data` | Bảng index: từ → offset + length |
| `data/meaning.data` | Nghĩa từ dạng bytes |

---

## 2. Gợi ý tự động (Autocomplete)

### Tính năng
- Gõ vài ký tự → hiện danh sách gợi ý bên dưới thanh tìm kiếm
- Kết hợp gợi ý local (Trie) + online (Datamuse API)
- Dùng bàn phím ↑↓ để chọn, Enter để tra cứu

### Thuật toán — Trie (Cây tiền tố) + Debounce

```
Keypress → Trie search (tức thì, 0ms)
         → Hiện gợi ý local ngay
         → Debounce 400ms → Gọi Datamuse API (background thread)
         → Merge local + online → Cập nhật gợi ý
```

**Trie hoạt động thế nào?**
- Mỗi ký tự là một node trong cây
- Gõ "hel" → duyệt từ root → h → e → l
- Từ node `l`, dùng DFS tìm tất cả từ: `hello`, `help`, `helmet`...
- Giới hạn 8 kết quả, sắp xếp theo alphabet

**Debounce là gì?**
- Khi gõ nhanh, app không gọi API mỗi phím bấm
- Chờ 400ms sau phím cuối cùng rồi mới gọi API
- Tránh spam API, tiết kiệm băng thông

### File liên quan
| File | Vai trò |
|---|---|
| `trie.py` | Cấu trúc dữ liệu Trie |
| `gui.py` | Logic autocomplete + debounce |
| `storage.py` | `prefix_trie()`, `prefix_bisect()` |

---

## 3. Tra cứu trực tuyến (Online Lookup)

### Tính năng
- Gọi API từ điển trực tuyến để lấy nghĩa đầy đủ
- Hiển thị theo Part of Speech (noun, verb, adjective...)
- Kèm ví dụ, từ đồng nghĩa, trái nghĩa
- Cache kết quả để không gọi lại API cùng từ

### Cơ chế hoạt động

```
Tra từ "hello"
    → Kiểm tra cache (online_cache.json)
    → Nếu có → Trả về từ cache (không cần internet)
    → Nếu không → Gọi API: dictionaryapi.dev/api/v2/entries/en/hello
    → Parse JSON → Tạo OnlineDictionaryEntry
    → Lưu vào cache → Hiển thị
```

**Cấu trúc dữ liệu trả về:**
```
OnlineDictionaryEntry
├── word: "hello"
├── phonetic: "/həˈloʊ/"
├── meanings:
│   ├── OnlineMeaning (noun)
│   │   └── definitions: [{definition, example, synonyms, antonyms}]
│   └── OnlineMeaning (verb)
│       └── definitions: [{definition, example, synonyms, antonyms}]
└── source_urls: [...]
```

### File liên quan
| File | Vai trò |
|---|---|
| `online_lookup.py` | Client API + cache + format |
| `data/online_cache.json` | Cache kết quả tra cứu |

---

## 4. Hệ thống ôn tập (Spaced Repetition)

### Tính năng
- Lưu từ vào danh sách ôn tập
- Mỗi ngày hiện danh sách "Due Today" — những từ cần ôn
- Bấm "Remember" hoặc "Again" để đánh giá
- App tự tính ngày ôn tiếp theo dựa trên kết quả

### Thuật toán — SM-2 (SuperMemo 2)

Mỗi từ có 3 thông số chính:
| Thông số | Ý nghĩa | Giá trị ban đầu |
|---|---|---|
| `interval_days` | Số ngày đến lần ôn tiếp | 1 |
| `ease_factor` | Hệ số dễ/khó | 2.5 |
| `next_review_date` | Ngày ôn tiếp theo | Ngày mai |

**Khi bấm "Remember" (nhớ):**
```
interval = interval × ease_factor    (ví dụ: 1 × 2.5 = 3 ngày)
ease_factor += 0.1                   (tăng dần → ôn ít hơn)
next_review = today + interval
```

**Khi bấm "Again" (quên):**
```
interval = 1                         (reset về 1 ngày)
ease_factor -= 0.2                   (giảm, tối thiểu 1.3)
next_review = tomorrow
```

**Ví dụ thực tế:**
```
Ngày 1: Học từ "algorithm"       → next = Ngày 2
Ngày 2: Nhớ → interval = 3      → next = Ngày 5
Ngày 5: Nhớ → interval = 8      → next = Ngày 13
Ngày 13: Quên → interval = 1    → next = Ngày 14
Ngày 14: Nhớ → interval = 3     → next = Ngày 17
```
→ Từ nào khó sẽ xuất hiện thường xuyên hơn, từ nào dễ sẽ thưa dần.

### File liên quan
| File | Vai trò |
|---|---|
| `srs.py` | ReviewStore + thuật toán SM-2 |
| `data/review.json` | Dữ liệu ôn tập |

---

## 5. Flashcards (Thẻ ghi nhớ)

### Tính năng
- **3 chế độ**: Due Today (cần ôn), All Words (tất cả từ), Custom Cards (thẻ tự tạo)
- **Thao tác**: Tạo, sửa, xóa, xáo trộn thẻ
- **Mini game**: Quiz (trắc nghiệm) và Match (ghép đôi)
- **Điều khiển**: Click trái (thẻ trước), giữa (lật thẻ), phải (thẻ sau)

### Cơ chế hoạt động

```
Flashcard Store (flashcards.json)
├── cards: dict[key → Flashcard]
│   └── Flashcard {front, back, note, tags}
│
├── upsert(front, back)  → Tạo/cập nhật thẻ
├── delete(front)         → Xóa thẻ (chỉ custom cards)
└── list_cards()          → Trả về danh sách đã sắp xếp
```

**Xóa flashcard:**
```
Bấm "✖ Delete" → normalize_word(front) → dict.pop(key) → save_json()
```
> Lưu ý: Chỉ xóa được thẻ custom. Thẻ từ dictionary chính không xóa được.

**Quiz mode**: Hiện từ + 4 đáp án ngẫu nhiên, chọn đúng/sai.
**Match mode**: Ghép từ với nghĩa trong thời gian giới hạn.

### File liên quan
| File | Vai trò |
|---|---|
| `flashcards.py` | FlashcardStore + CRUD |
| `gui.py` | UI flashcard + quiz + match |
| `data/flashcards.json` | Dữ liệu thẻ |

---

## 6. Kiểm tra ngữ pháp (Grammar Checker)

### Tính năng
- **Kiểm tra offline** (rule-based): Nhanh, không cần internet
- **Kiểm tra AI** (Gemini): Chính xác hơn, cần internet
- Gạch chân lỗi, hiện gợi ý sửa và lý do

### Thuật toán — Rule-based Pattern Matching

App kiểm tra **10 loại lỗi** theo thứ tự:

| # | Loại lỗi | Ví dụ | Sửa thành |
|---|---|---|---|
| 1 | Viết hoa đầu câu | `hello world` | `Hello world` |
| 2 | Đại từ "I" | `i am happy` | `I am happy` |
| 3 | Hòa hợp chủ-vị | `He are smart` | `He is smart` |
| 4 | Mạo từ a/an | `a apple` | `an apple` |
| 5 | Thì sau "did" | `did went` | `did go` |
| 6 | Phủ định kép | `don't have no` | `don't have any` |
| 7 | Từ dễ nhầm | `your smart` | `you're smart` |
| 8 | Lỗi chính tả | `teh` | `the` |
| 9 | Cụm từ thừa | `ATM machine` | `ATM` |
| 10 | Dấu câu cuối | `Hello world` | `Hello world.` |

**Phát hiện lỗi chính tả — difflib.get_close_matches():**
- Dùng thuật toán **Ratcliff/Obershelp** (SequenceMatcher)
- So sánh từ gõ với từ điển, tìm từ gần nhất với `cutoff=0.84` (84% giống)
- Ví dụ: `"algoritm"` → match với `"algorithm"` (similarity > 0.84)

**Phát hiện "your" vs "you're":**
- Nếu từ sau `"your"` là tính từ (`smart`, `beautiful`, `great`...) → gợi ý `"you're"`
- Dùng bảng tra cứu (lookup table) với ~30 tính từ phổ biến

### File liên quan
| File | Vai trò |
|---|---|
| `grammar.py` | Engine kiểm tra ngữ pháp 10 luật |
| `ai.py` | `grammar_correct()` — kiểm tra bằng AI |

---

## 7. Trợ lý AI (AI Assistant)

### Tính năng
- **Hỏi đáp**: Hỏi bất kỳ câu hỏi tiếng Anh nào
- **Giải thích từ**: Core meaning, academic meaning, contexts, examples
- **Dịch thuật**: Tự động phát hiện ngôn ngữ (EN↔VI)
- **Viết luận**: 3 chế độ: Outline (dàn bài), Write (viết), Improve (cải thiện)
- **Nhận diện ảnh**: OCR (trích xuất text) và mô tả ảnh (Gemini Vision)

### Cơ chế hoạt động

```
Câu hỏi của người dùng
    → Sanitize (ẩn email, phone)
    → Tạo prompt chuyên biệt
    → Gọi Google Gemini API
    → Parse kết quả JSON
    → Lưu cache → Hiển thị
```

**Bảo mật dữ liệu:**
```python
# Trước khi gửi lên API, ẩn thông tin nhạy cảm:
"Contact me at john@email.com"  →  "Contact me at [email]"
"Call 0912345678"               →  "Call [phone]"
```

**Cache thông minh:**
- Mỗi câu hỏi được tạo key duy nhất: `"từ|domain|ngôn_ngữ"`
- Nếu hỏi lại cùng câu → trả về từ cache, không tốn API call

**Nhận diện ảnh (Gemini Vision):**
```
Dán ảnh (Ctrl+V) hoặc chọn file
    → Convert sang Base64
    → Gửi kèm prompt lên Gemini API
    → Trả về text (OCR) hoặc mô tả ảnh
```

### File liên quan
| File | Vai trò |
|---|---|
| `ai.py` | GeminiExplainClient — tất cả tính năng AI |
| `gemini_api.py` | HTTP wrapper cho Gemini API |
| `data/ai_cache.json` | Cache kết quả AI |

---

## 8. Phát âm (Text-to-Speech)

### Tính năng
- Phát âm từ bằng giọng nói tự nhiên
- Hiển thị phiên âm IPA (ví dụ: `/həˈloʊ/`)
- Cache file audio để phát lại nhanh

### Cơ chế hoạt động

```
Bấm "▶ Play"
    → Kiểm tra audio_cache/ có file MP3 chưa
    → Nếu có → pygame phát file MP3
    → Nếu không → gTTS tạo audio → Lưu vào cache → Phát
```

### File liên quan
| File | Vai trò |
|---|---|
| `tts.py` | PhoneticsService — IPA + audio |
| `data/audio_cache/` | Thư mục chứa file MP3 đã tạo |
| `data/phonetic_cache.json` | Cache dữ liệu IPA |

---

## 9. Giao diện & Theme

### 4 Theme có sẵn

| Theme | Phong cách | Nền | Màu chủ đạo |
|---|---|---|---|
| **Default** | Dark tím + hiệu ứng glow | `#0b0e1a` | `#7c5cfc` |
| **Blue White** | Light xanh trắng | `#eef3fb` | `#0f52ba` |
| **Black White** | Dark navy xanh | `#060735` | `#4a6bff` |
| **Black Gold** | Dark đen vàng sang trọng | `#151515` | `#d4af37` |

### Cơ chế thay đổi Theme

```
Chọn theme mới trên sidebar
    → _snapshot_inputs()    (Lưu text đang gõ)
    → _configure_theme()   (Load bảng ~15 mã màu)
    → save_json()          (Ghi vào ui_settings.json)
    → main_shell.destroy() (XÓA toàn bộ UI cũ)
    → _build_layout()      (DỰNG LẠI UI mới với màu mới)
    → show_page()          (Hiện lại trang đang xem)
    → _restore_panels()    (Khôi phục text đã lưu)
```

**Hiệu ứng Glow (chỉ theme Default):**
- Vẽ 4 vùng sáng mờ (tím, xanh, hồng, cyan) trên Canvas
- Mỗi vùng = 8 hình oval đồng tâm với độ sáng giảm dần
- Tự động vẽ lại khi resize cửa sổ (debounce 150ms)

**Font size**: 4 mức (90%, 100%, 115%, 130%) — tất cả font được nhân với hệ số scale.

---

## 10. Nhập dữ liệu (Import)

### Tính năng
- Import từ file TXT, CSV, JSON
- Import từ URL
- Import từ clipboard
- Tự động phát hiện format và tách từ/nghĩa

### Cơ chế
```
File/URL/Clipboard
    → Đọc nội dung
    → Phát hiện format (tab-separated, comma, JSON...)
    → Parse thành dict {word: meaning}
    → normalize_word() cho mỗi từ
    → upsert_entries() — merge vào dictionary hiện tại
    → Rebuild index + trie + alphabet
```

### File liên quan
| File | Vai trò |
|---|---|
| `importers.py` | Parse file/URL/clipboard |
| `storage.py` | `upsert_entries()` — merge + rebuild |

---

## 11. Kiến trúc lưu trữ

### Sơ đồ tổng thể

```
data/
├── index.data            ← Hash index (tab-separated: word → offset + length)
├── meaning.data          ← Raw bytes (nghĩa từ, đọc bằng mmap)
├── alphabet.idx          ← Sorted word list (cho bisect search)
├── trie.idx              ← JSON chứa danh sách từ (cho Trie)
├── review.json           ← SRS data (SM-2 parameters)
├── flashcards.json       ← Custom flashcard data
├── ai_cache.json         ← Cache kết quả AI
├── online_cache.json     ← Cache tra cứu online
├── phonetic_cache.json   ← Cache IPA
├── translation_cache.json ← Cache dịch thuật
├── ui_settings.json      ← Theme + font size
├── vietnamese_meaning.json ← Nghĩa tiếng Việt
└── audio_cache/          ← File MP3 phát âm
```

### Các thuật toán tra cứu

| Phương pháp | Thuật toán | Độ phức tạp | Dùng khi |
|---|---|---|---|
| Hash Lookup | `dict[key]` | O(1) | Tra chính xác 1 từ |
| Trie Search | DFS trên cây tiền tố | O(k + m) | Autocomplete |
| Bisect Search | Binary search | O(log n) | Duyệt theo alphabet |
| mmap Read | Memory-mapped I/O | O(1) | Đọc nghĩa từ file |

> k = độ dài prefix, m = số kết quả, n = tổng số từ

---

## 12. Đóng gói ứng dụng

### Công cụ: PyInstaller

```
Code Python + Python Interpreter + DLL + Assets
    → PyInstaller đóng gói tất cả
    → DictionaryApp.exe (1 file duy nhất)
```

### 4 bước đóng gói

| Bước | Tên | Mô tả |
|---|---|---|
| 1 | **Analysis** | Phân tích tất cả import, tìm dependency |
| 2 | **PYZ** | Biên dịch .py → bytecode, nén vào archive |
| 3 | **EXE** | Gộp bootloader + interpreter + bytecode + assets |
| 4 | **Output** | `dist/DictionaryApp.exe` |

### Cấu hình quan trọng (`DictionaryApp.spec`)

```python
# Entry point
['app.py']

# File đi kèm (icon, ảnh)
datas=[('dictionary_app/assets', 'dictionary_app/assets')]

# Module ẩn (PyInstaller không tự phát hiện)
hiddenimports=['dictionary_app.gui', 'dictionary_app.storage', ...]

# Không hiện console (chỉ hiện GUI)
console=False

# Nén bằng UPX
upx=True

# Icon file
icon='dictionary_app/assets/app_icon.ico'
```

### Lệnh đóng gói

```bash
pip install pyinstaller
pyinstaller DictionaryApp.spec --noconfirm
# Output: dist/DictionaryApp.exe
```

---

## 📊 Tổng kết các thuật toán đã dùng

| Thuật toán | Ứng dụng | File |
|---|---|---|
| **Hash Map** (dict) | Tra từ O(1) | `storage.py` |
| **Trie** (cây tiền tố) | Autocomplete | `trie.py` |
| **Binary Search** (bisect) | Duyệt alphabet | `storage.py` |
| **Memory-Mapped I/O** (mmap) | Đọc nghĩa từ nhanh | `storage.py` |
| **SM-2** (SuperMemo) | Lên lịch ôn tập | `srs.py` |
| **Ratcliff/Obershelp** (difflib) | Phát hiện lỗi chính tả | `grammar.py` |
| **Rule-based Matching** | Kiểm tra ngữ pháp | `grammar.py` |
| **Debounce + Threading** | Autocomplete online | `gui.py` |
| **Caching** (JSON) | Giảm API calls | `ai.py`, `online_lookup.py` |

---

*Tài liệu này được tạo ngày 23/03/2026 cho project [Dictionary App 2.0](https://github.com/thachnood976-hash/Dictionary).*
