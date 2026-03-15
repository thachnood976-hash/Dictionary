# LexiCore — Product Requirements Document (PRD)

**Project Name:** LexiCore — AI-Powered Desktop Dictionary & Vocabulary Learning System  
**Version:** 1.0  
**Date:** March 8, 2026  
**Author:** Software Engineering Team  
**Status:** Draft  

---

## Table of Contents

1. [Product Vision](#1-product-vision)  
2. [Goals and Use Cases](#2-goals-and-use-cases)  
3. [System Architecture](#3-system-architecture)  
4. [Core Features](#4-core-features)  
5. [UI/UX Design](#5-uiux-design)  
6. [Animations and Interactions](#6-animations-and-interactions)  
7. [Functional Requirements](#7-functional-requirements)  
8. [Non-Functional Requirements](#8-non-functional-requirements)  
9. [Suggested Tech Stack](#9-suggested-tech-stack)  
10. [Conclusion](#10-conclusion)  

---

## 1. Product Vision

### 1.1 Overview

**LexiCore** is a next-generation, AI-powered offline desktop dictionary and vocabulary-learning platform. It is built for speed, intelligence, and visual immersion. Unlike conventional dictionary tools that rely on basic string lookups and plain-text displays, LexiCore combines high-performance data indexing, fuzzy-matching algorithms, phonetic error tolerance, and AI-assisted features into a single polished desktop experience.

### 1.2 Design Philosophy

The product follows a **"Liquid Glass"** design language — a modern aesthetic inspired by depth, refraction, and physicality. Every surface in the application behaves like semi-transparent glass: frosted panels blur the content beneath them, dynamic background images tint and refract through the UI chrome, and subtle cursor-reactive lighting effects give the interface a sense of tangible, three-dimensional depth.

### 1.3 Target Audience

| Segment | Description |
|---|---|
| **University students** | Learners who need fast, reliable word lookup across multiple subjects and languages. |
| **Language learners** | Individuals studying English (or other languages) who benefit from phonetic search, audio pronunciation, and spaced-repetition flashcards. |
| **Writers & researchers** | Professionals who require an offline reference tool with rich definitions, context sentences, and part-of-speech annotations. |
| **Power users** | Users who value sub-millisecond lookup times, keyboard shortcuts, and advanced customization. |

### 1.4 Value Proposition

> *"The fastest, most beautiful dictionary you have ever used — entirely offline, endlessly intelligent."*

- **Instant lookup** — sub-5 ms word retrieval from a local indexed database.  
- **Forgiveness in search** — fuzzy matching and phonetic tolerance mean users don't need to spell perfectly.  
- **Immersive learning** — multimedia support (images, audio, contextual backgrounds) transforms passive lookup into active vocabulary acquisition.  
- **Zero cloud dependency** — all core features operate fully offline after initial data setup.

---

## 2. Goals and Use Cases

### 2.1 Primary Goals

| ID | Goal | Success Metric |
|---|---|---|
| G-01 | Extremely fast word lookup | Average lookup latency ≤ 5 ms for a 300k-word corpus |
| G-02 | Intelligent search | Autocomplete, fuzzy matching, and phonetic correction surface the correct word ≥ 95% of the time within the top 5 suggestions |
| G-03 | Multimedia-rich definitions | ≥ 80% of common words display at least one contextual image and one audio pronunciation clip |
| G-04 | Vocabulary learning via spaced repetition | Users can build, review, and export Anki-style decks directly from the definition view |
| G-05 | Premium visual experience | UI consistently renders at ≥ 60 fps with all glass and animation effects enabled |
| G-06 | Full offline operation | 100% of core features functional without a network connection |

### 2.2 Use Cases

#### UC-01: Quick Word Lookup
> **Actor:** Student  
> **Trigger:** User presses the global hotkey (e.g., `Ctrl+Shift+L`) or clicks the search bar.  
> **Flow:**  
> 1. The search bar gains focus and the cursor blinks.  
> 2. As the user types, autocomplete suggestions appear in a fluid dropdown.  
> 3. The user selects a suggestion (or presses Enter).  
> 4. The search bar smoothly morphs into a **Definition Card** displaying the word, phonetic transcription, parts of speech, definitions, and example sentences.  
> 5. A contextual background image crossfades in behind the card, tinting the glass panels.  
> **Postcondition:** The definition is displayed in under 50 ms from keystroke to render.

#### UC-02: Voice Search
> **Actor:** Language learner  
> **Trigger:** User clicks the microphone icon or presses `Ctrl+M`.  
> **Flow:**  
> 1. The microphone icon transforms into a live audio waveform visualizer.  
> 2. Ripple feedback animates outward in sync with audio amplitude.  
> 3. The recognized word appears in the search bar in real time.  
> 4. On silence (or manual stop), the best-match word is selected and the Definition Card opens.  
> **Postcondition:** Voice input is transcribed and matched even with imperfect pronunciation.

#### UC-03: Saving a Word to a Deck
> **Actor:** Vocabulary learner  
> **Trigger:** User drags a Definition Card toward the deck panel.  
> **Flow:**  
> 1. As the card is dragged, it tilts toward the cursor with a 3D perspective effect.  
> 2. A "deck drop zone" glows and pulsates to indicate readiness.  
> 3. On release, the card snaps into the deck with a **liquid snap animation** — the edges ripple as the card shrinks and slots into position.  
> 4. A brief toast notification confirms the save.  
> **Postcondition:** The word (with definition, audio, and image) is stored in the selected deck for spaced-repetition review.

#### UC-04: Reviewing a Deck (Spaced Repetition)
> **Actor:** Student  
> **Trigger:** User navigates to the "Decks" panel and taps "Study".  
> **Flow:**  
> 1. Cards appear one at a time with the target word face-up.  
> 2. User attempts to recall the definition, then flips the card.  
> 3. User self-rates recall quality (Again / Hard / Good / Easy).  
> 4. The SRS algorithm schedules the next review date for each card.  
> **Postcondition:** Deck state is persisted locally; review statistics are updated.

#### UC-05: Exploring Related Words
> **Actor:** Writer  
> **Trigger:** User clicks a synonym, antonym, or "related words" link on the Definition Card.  
> **Flow:**  
> 1. A new Definition Card slides in from the right, pushing the current card to a breadcrumb stack on the left.  
> 2. The user can navigate back through the stack.  
> **Postcondition:** The user has explored a chain of semantically related words without losing navigation context.

---

## 3. System Architecture

### 3.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        DESKTOP SHELL                            │
│                    (Tauri / Electron)                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  FRONTEND (React 18+)                     │  │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Search  │  │Definition│  │  Deck    │  │ Settings │  │  │
│  │  │  Bar    │  │  Canvas  │  │ Manager  │  │  Panel   │  │  │
│  │  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │  │
│  │       │             │             │              │        │  │
│  │  ┌────▼─────────────▼─────────────▼──────────────▼────┐  │  │
│  │  │          State Management (Zustand / Redux)        │  │  │
│  │  └────────────────────┬───────────────────────────────┘  │  │
│  │                       │  HTTP / WebSocket                │  │
│  └───────────────────────┼───────────────────────────────────┘  │
│                          │                                      │
│  ┌───────────────────────▼───────────────────────────────────┐  │
│  │              LOCAL API SERVER (FastAPI)                    │  │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐             │  │
│  │  │ Search   │  │ Dictionary│  │    SRS     │             │  │
│  │  │ Engine   │  │   Data    │  │  Engine    │             │  │
│  │  │(Trie +   │  │  Access   │  │(SM-2 algo) │             │  │
│  │  │ BK-Tree) │  │  Layer    │  │            │             │  │
│  │  └──────────┘  └───────────┘  └────────────┘             │  │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐             │  │
│  │  │ Phonetic │  │   Media   │  │  AI/NLP    │             │  │
│  │  │ Encoder  │  │  Manager  │  │  Module    │             │  │
│  │  │(Metaphone│  │(img/audio)│  │(optional)  │             │  │
│  │  │/Soundex) │  │           │  │            │             │  │
│  │  └──────────┘  └───────────┘  └────────────┘             │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                      │
│  ┌───────────────────────▼───────────────────────────────────┐  │
│  │                 DATA LAYER                                │  │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────────────────┐ │  │
│  │  │  SQLite  │  │   Media   │  │  User Data (decks,     │ │  │
│  │  │  (words, │  │   Store   │  │  settings, history)    │ │  │
│  │  │  indexes)│  │  (images, │  │                        │ │  │
│  │  │          │  │   audio)  │  │                        │ │  │
│  │  └──────────┘  └───────────┘  └────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │         OPTIONAL C++ EXTENSIONS (via pybind11)            │  │
│  │  High-perf trie traversal · Levenshtein automaton         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Descriptions

| Component | Responsibility | Technology |
|---|---|---|
| **Desktop Shell** | Native window management, system tray, global hotkeys, auto-update | Tauri (preferred) or Electron |
| **Frontend** | All UI rendering, animations, state management, user interaction | React 18+, Tailwind CSS, Framer Motion, optional WebGL shaders |
| **Local API Server** | Serves dictionary data to the frontend via REST and/or WebSocket | Python 3.12+, FastAPI, Uvicorn |
| **Search Engine** | Trie-based prefix search, BK-Tree for fuzzy matching, phonetic index | Python (with optional C++ extensions) |
| **Dictionary Data Access** | Reads and writes to the word database, manages indexes | SQLAlchemy or direct SQLite via `aiosqlite` |
| **SRS Engine** | Implements the SM-2 spaced-repetition algorithm for deck reviews | Python |
| **Phonetic Encoder** | Generates Metaphone / Double Metaphone / Soundex codes for phonetic search | Python `metaphone` / custom module |
| **Media Manager** | Stores, retrieves, and caches images and audio clips associated with words | Python, local file system |
| **AI/NLP Module** | (Optional) Context-aware definition ranking, AI-generated example sentences, word-relationship graphs | Local LLM (e.g., llama.cpp) or offline NLP models |
| **C++ Extensions** | Performance-critical hot paths: trie traversal, Levenshtein distance computation | C++ via `pybind11` |

### 3.3 Communication Flow

```
User Input → Frontend (React) 
    ──[HTTP POST /api/search or WebSocket message]──▶ FastAPI Server
        ──▶ Search Engine (Trie + BK-Tree + Phonetic Index)
        ──▶ Data Access Layer (SQLite)
        ◀── Results (JSON: word, definitions, media paths, phonetics)
    ◀── Response rendered in Definition Canvas
```

- **REST endpoints** are used for stateless lookups (`GET /api/search?q=...`, `GET /api/word/{id}`).  
- **WebSocket** is used for streaming autocomplete suggestions as the user types, providing real-time, low-latency updates.

---

## 4. Core Features

### 4.1 Feature Matrix

| ID | Feature | Priority | Description |
|---|---|---|---|
| F-01 | **Instant Word Lookup** | P0 (Critical) | Sub-5 ms retrieval from a locally indexed database of 300k+ words. |
| F-02 | **Autocomplete** | P0 | Real-time prefix-based suggestions streamed via WebSocket as the user types. |
| F-03 | **Fuzzy Matching** | P0 | BK-Tree with configurable edit distance (default: 2) surfaces approximate matches for misspelled queries. |
| F-04 | **Phonetic Error Tolerance** | P1 (High) | Metaphone / Double Metaphone encoding allows searching by pronunciation (e.g., "nolej" → "knowledge"). |
| F-05 | **Voice Search** | P1 | Local speech-to-text transcription via Whisper (or browser Web Speech API) with real-time waveform visualization. |
| F-06 | **Multimedia Definitions** | P1 | Contextual images and audio pronunciation clips embedded in the definition view. |
| F-07 | **Spaced Repetition Decks** | P1 | Anki-style flashcard system with SM-2 scheduling, drag-to-save interaction, and deck management. |
| F-08 | **Word Relationship Graph** | P2 (Medium) | Interactive visualization of synonyms, antonyms, hypernyms, and related words as a node graph. |
| F-09 | **History & Bookmarks** | P2 | Searchable lookup history and user-defined bookmark lists. |
| F-10 | **AI-Assisted Features** | P3 (Low) | AI-generated example sentences, context-aware definition ranking, and conversational word explanations via a local LLM. |
| F-11 | **Export & Sharing** | P2 | Export decks to Anki-format `.apkg`, share individual definitions as styled images or PDFs. |
| F-12 | **Multilingual Support** | P3 | Extensible architecture supporting additional language dictionaries as plug-in data packs. |
| F-13 | **Global Hotkey** | P1 | System-wide keyboard shortcut to summon LexiCore from any application. |
| F-14 | **Offline-First Architecture** | P0 | All core features operate without an internet connection. |

### 4.2 Search Engine Details

The search engine is the heart of LexiCore. It employs a **multi-strategy search pipeline**:

```
Query "nolej"
   │
   ├──▶ [Stage 1] Exact Match (Hash lookup) ──▶ "nolej" not found
   │
   ├──▶ [Stage 2] Prefix Match (Trie traversal) ──▶ no useful prefix matches
   │
   ├──▶ [Stage 3] Fuzzy Match (BK-Tree, edit distance ≤ 2)
   │       └──▶ Candidates: "knowledge" (distance 4) — rejected
   │
   └──▶ [Stage 4] Phonetic Match (Double Metaphone)
           └──▶ metaphone("nolej") = "NLJ"
           └──▶ metaphone("knowledge") = "NLJ" ✓ — MATCH
           └──▶ Result: "knowledge"
```

All four stages run in parallel where possible; the fastest confident match is returned immediately, while lower-priority stages provide fallback results.

### 4.3 Spaced Repetition System (SRS)

The SRS module implements a modified **SM-2 algorithm**:

| Parameter | Description | Default |
|---|---|---|
| `easiness_factor` | Multiplier for interval growth | 2.5 |
| `interval` | Days until next review | 1 (initial) |
| `repetitions` | Consecutive correct recalls | 0 |
| `quality` | User self-rating (0–5) | — |

**Review flow:**

1. A card is presented (target word face-up).  
2. User recalls (or fails to recall) the definition.  
3. User taps a rating button: **Again** (0) / **Hard** (2) / **Good** (4) / **Easy** (5).  
4. The algorithm updates `easiness_factor`, `interval`, and `repetitions`.  
5. Next review date = `today + interval`.

---

## 5. UI/UX Design

### 5.1 Design Language — "Liquid Glass"

The **Liquid Glass** design language is the visual identity of LexiCore. It draws inspiration from real-world materials — frosted glass, water surfaces, and optical refraction — and translates them into GPU-accelerated interface elements.

#### Core Principles

| Principle | Implementation |
|---|---|
| **Depth & Layering** | Multiple frosted-glass panels stacked with varying blur intensities (8 px – 40 px) create a sense of spatial depth. |
| **Color Refraction** | Dynamic background images (contextual to the current word) bleed color through semi-transparent surfaces, tinting the glass panels organically. |
| **Edge Highlighting** | Thin (1 px), bright border lines on glass panel edges simulate light catching on glass edges. Use `border: 1px solid rgba(255,255,255,0.18)`. |
| **Cursor-Reactive Lighting** | A soft radial gradient follows the cursor position, simulating a light source moving across the glass surface. Implemented via CSS `radial-gradient` positioned at `pointer.x, pointer.y`. |
| **Motion as Material** | All transitions use spring-based easing (Framer Motion `spring` type) to feel physical and organic rather than mechanical. |

#### CSS Foundation

```css
/* Liquid Glass base panel */
.glass-panel {
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(24px) saturate(1.4);
  -webkit-backdrop-filter: blur(24px) saturate(1.4);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

/* Cursor-reactive highlight overlay */
.glass-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: radial-gradient(
    600px circle at var(--mouse-x) var(--mouse-y),
    rgba(255, 255, 255, 0.06),
    transparent 40%
  );
  pointer-events: none;
}
```

### 5.2 Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│  [Dynamic Background Image — full bleed, crossfade]          │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  TOP BAR (glass)                                        ││
│  │  [☰ Menu]  [🔍 Search Bar ........................ 🎤]  ││
│  │  [⚡ Lookup: 2.3ms]                                     ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────┐  ┌─────────────────────────┐│
│  │  DEFINITION CANVAS (glass)  │  │  SIDEBAR (glass)        ││
│  │                             │  │                         ││
│  │  knowledge                  │  │  📚 Decks               ││
│  │  /ˈnɒl.ɪdʒ/                │  │  ├─ English Vocab (42)  ││
│  │                             │  │  ├─ GRE Words (128)     ││
│  │  noun · uncountable         │  │  └─ + New Deck          ││
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━  │  │                         ││
│  │  1. Facts, information,     │  │  📖 History             ││
│  │     and skills acquired     │  │  ├─ knowledge           ││
│  │     through experience or   │  │  ├─ ephemeral           ││
│  │     education.              │  │  ├─ ubiquitous          ││
│  │                             │  │  └─ ...                 ││
│  │  "a thirst for knowledge"   │  │                         ││
│  │                             │  │  🔗 Related Words       ││
│  │  🔊 Play Audio              │  │  ├─ wisdom             ││
│  │  🖼️ [Contextual Image]      │  │  ├─ understanding      ││
│  │                             │  │  └─ awareness          ││
│  │  Synonyms: wisdom, insight  │  │                         ││
│  │  Antonyms: ignorance        │  │                         ││
│  └─────────────────────────────┘  └─────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  BOTTOM BAR (glass)                                     ││
│  │  [Total Words: 312,847]  [Theme: Dark]  [⚙ Settings]   ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 5.3 Color System

| Token | Dark Mode | Light Mode | Usage |
|---|---|---|---|
| `--bg-primary` | `#0a0a0f` | `#f5f5fa` | Application background |
| `--glass-bg` | `rgba(255,255,255,0.06)` | `rgba(0,0,0,0.04)` | Panel fills |
| `--glass-border` | `rgba(255,255,255,0.12)` | `rgba(0,0,0,0.08)` | Panel borders |
| `--text-primary` | `#e8e8ed` | `#1a1a2e` | Body text |
| `--text-secondary` | `#8b8ba3` | `#6e6e87` | Muted text |
| `--accent-blue` | `#5b9dff` | `#3a7bfd` | Interactive elements, links |
| `--pos-noun` | `#7dd3fc` | `#0284c7` | Noun POS badge |
| `--pos-verb` | `#a78bfa` | `#7c3aed` | Verb POS badge |
| `--pos-adj` | `#fbbf24` | `#d97706` | Adjective POS badge |
| `--pos-adv` | `#34d399` | `#059669` | Adverb POS badge |
| `--success` | `#22c55e` | `#16a34a` | Correct recall rating |
| `--danger` | `#ef4444` | `#dc2626` | Failed recall rating |

### 5.4 Typography

| Element | Font | Weight | Size |
|---|---|---|---|
| Target word | **Outfit** | 700 | 48 px |
| Phonetic transcription | **JetBrains Mono** | 400 | 16 px |
| POS badge | **Inter** | 600 | 12 px (uppercase) |
| Definition body | **Inter** | 400 | 16 px / 1.7 line-height |
| Example sentence | **Inter** | 400 italic | 15 px |
| UI labels | **Inter** | 500 | 13 px |
| Metrics display | **JetBrains Mono** | 500 | 11 px |

---

## 6. Animations and Interactions

### 6.1 Animation Inventory

All animations are implemented with **Framer Motion** (React) and optionally enhanced by **WebGL shaders** for advanced GPU effects.

#### 6.1.1 Search Bar → Definition Card Morph

| Property | From (Search Bar) | To (Definition Card) |
|---|---|---|
| `width` | `480px` | `640px` |
| `height` | `52px` | `auto (≈ 520px)` |
| `borderRadius` | `26px` | `20px` |
| `y` | `0` | `+40px` |
| `background` | Glass blur 12px | Glass blur 24px |
| Duration | — | `0.5s` spring (stiffness: 260, damping: 25) |

**Behavior:** When the user selects a word, the search bar container smoothly expands into the Definition Card. The text input fades out as the definition content fades in. The background behind the card crossfades to a contextual image.

```jsx
// Framer Motion layout animation
<motion.div
  layout
  transition={{ type: "spring", stiffness: 260, damping: 25 }}
  className="glass-panel"
>
  {isSearchMode ? <SearchInput /> : <DefinitionCard word={result} />}
</motion.div>
```

#### 6.1.2 Voice Search Waveform

| Phase | Animation |
|---|---|
| **Activation** | Microphone icon scales up (1 → 1.2) and morphs into a circular waveform container. |
| **Listening** | A `<canvas>` element renders a real-time audio waveform using Web Audio API's `AnalyserNode`. Bars animate with spring physics. |
| **Ripple Feedback** | Concentric circles emanate from the waveform center, with radius and opacity driven by `AnalyserNode.getByteFrequencyData()` amplitude. |
| **Recognition** | The waveform collapses back into the search bar, and recognized text types itself in with a typewriter effect. |

#### 6.1.3 Autocomplete Dropdown

| Property | Value |
|---|---|
| Container enter | `opacity: 0 → 1`, `scaleY: 0.95 → 1`, `y: -8 → 0` over `0.2s` spring |
| Item stagger | Each suggestion animates in with a `0.03s` stagger delay |
| Item hover | `background` brightens by +4% opacity, left border accent slides in from `scaleX: 0 → 1` |
| Item exit | Reverse of enter, `0.15s` |

#### 6.1.4 Drag-to-Deck Interaction

| Phase | Animation |
|---|---|
| **Drag Start** | Card lifts: `scale: 1.03`, `boxShadow` deepens, `rotate3d` tilts toward the cursor direction. |
| **Dragging** | Card follows the cursor with slight inertia (spring damping). A ghost trail of 2–3 faded copies lingers behind. |
| **Over Drop Zone** | Deck panel border glows (`box-shadow: 0 0 20px var(--accent-blue)`), a "slot" opens in the deck list with a spring animation. |
| **Drop** | Card shrinks (`scale: 1.0 → 0.15`) and snaps into the slot. Edges ripple outward with a liquid distortion effect (CSS filter or WebGL). |
| **Confirmation** | A subtle "plop" haptic-style bounce (scale: `0.15 → 0.18 → 0.15`) and a toast notification slides up. |

#### 6.1.5 Cursor-Reactive Glass Lighting

Implemented as a CSS custom property update on `mousemove`:

```javascript
document.addEventListener('mousemove', (e) => {
  document.querySelectorAll('.glass-panel').forEach((panel) => {
    const rect = panel.getBoundingClientRect();
    panel.style.setProperty('--mouse-x', `${e.clientX - rect.left}px`);
    panel.style.setProperty('--mouse-y', `${e.clientY - rect.top}px`);
  });
});
```

This drives the `radial-gradient` in the `::before` pseudo-element of all `.glass-panel` elements, creating the illusion of a light source following the cursor.

### 6.2 Performance Considerations for Animations

| Constraint | Strategy |
|---|---|
| **60 fps target** | All animations use `transform` and `opacity` only (GPU-composited properties). Avoid animating `width`, `height`, `top`, `left`. |
| **Backdrop filter cost** | Limit `backdrop-filter: blur()` to ≤ 3 simultaneous panels. Use `will-change: backdrop-filter` sparingly. |
| **WebGL optional** | Advanced effects (liquid ripple, refraction shaders) are opt-in and disabled by default on lower-tier hardware. Detect via `navigator.gpu` or frame-rate monitoring. |
| **Reduced motion** | Respect `prefers-reduced-motion` media query. Disable all spring animations and crossfades; use instant transitions. |

---

## 7. Functional Requirements

### 7.1 Search & Lookup

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | The system shall return exact word matches in ≤ 5 ms from a local database. | P0 |
| FR-02 | The system shall provide real-time autocomplete suggestions as the user types, with ≤ 30 ms latency per keystroke. | P0 |
| FR-03 | The system shall support fuzzy matching using BK-Tree with a configurable maximum edit distance (default: 2). | P0 |
| FR-04 | The system shall support phonetic search using Double Metaphone encoding, tolerating common pronunciation-based misspellings. | P1 |
| FR-05 | The system shall support voice input via local speech-to-text, displaying a live waveform during recording. | P1 |
| FR-06 | The system shall display a performance metric (lookup latency in milliseconds) on the Definition Canvas. | P2 |
| FR-07 | The system shall maintain a searchable history of the last 1,000 lookups. | P2 |

### 7.2 Definition Display

| ID | Requirement | Priority |
|---|---|---|
| FR-08 | The Definition Canvas shall display: target word, phonetic transcription (IPA), parts of speech (color-coded), numbered definitions, and example sentences. | P0 |
| FR-09 | The system shall display a contextual image relevant to the word, sourced from the local media store. | P1 |
| FR-10 | The system shall play audio pronunciation clips for supported words. | P1 |
| FR-11 | The system shall display synonyms, antonyms, and related words with clickable navigation. | P1 |
| FR-12 | The Definition Canvas background image shall influence the glass panel color palette through color refraction. | P2 |

### 7.3 Vocabulary & SRS

| ID | Requirement | Priority |
|---|---|---|
| FR-13 | Users shall be able to create, rename, and delete decks. | P1 |
| FR-14 | Users shall be able to save a word to a deck via drag-and-drop from the Definition Canvas. | P1 |
| FR-15 | The SRS engine shall implement the SM-2 algorithm, scheduling review cards based on user-rated recall quality. | P1 |
| FR-16 | The system shall display per-deck statistics: total cards, cards due today, average easiness factor. | P2 |
| FR-17 | Users shall be able to export decks to Anki `.apkg` format. | P2 |

### 7.4 System & Settings

| ID | Requirement | Priority |
|---|---|---|
| FR-18 | The application shall support a system-wide global hotkey to summon the main window. | P1 |
| FR-19 | The application shall support Dark and Light themes. | P1 |
| FR-20 | The application shall allow users to configure: fuzzy match threshold, autocomplete result count, SRS difficulty modifiers, animation intensity. | P2 |
| FR-21 | All user data (decks, history, settings) shall be stored in a local SQLite database. | P0 |
| FR-22 | The application shall start in ≤ 3 seconds on a mid-range system (Intel i5, 8 GB RAM, SSD). | P1 |

---

## 8. Non-Functional Requirements

### 8.1 Performance

| ID | Requirement | Target |
|---|---|---|
| NFR-01 | Word lookup latency | ≤ 5 ms (p99) for a 300k-word corpus |
| NFR-02 | Autocomplete suggestion latency | ≤ 30 ms per keystroke |
| NFR-03 | Application cold start time | ≤ 3 seconds |
| NFR-04 | Memory usage (idle) | ≤ 200 MB |
| NFR-05 | Memory usage (active search) | ≤ 350 MB |
| NFR-06 | UI frame rate | ≥ 60 fps with all animations enabled |

### 8.2 Reliability & Data Integrity

| ID | Requirement | Target |
|---|---|---|
| NFR-07 | Data durability | Zero data loss for user decks and settings under normal operation. SQLite WAL mode enabled. |
| NFR-08 | Crash recovery | Application resumes to last state within 2 seconds after an unexpected termination. |
| NFR-09 | Graceful degradation | If media files are missing, the Definition Canvas displays a placeholder and does not crash. |

### 8.3 Usability

| ID | Requirement | Target |
|---|---|---|
| NFR-10 | Keyboard navigability | All primary features accessible via keyboard shortcuts without mouse. |
| NFR-11 | Accessibility | WCAG 2.1 AA compliance for text contrast, focus indicators, and screen reader compatibility. |
| NFR-12 | Reduced motion support | All animations respect the `prefers-reduced-motion` OS setting. |
| NFR-13 | Onboarding | First-time users receive a brief interactive tutorial (≤ 60 seconds) highlighting core features. |

### 8.4 Portability & Compatibility

| ID | Requirement | Target |
|---|---|---|
| NFR-14 | Supported platforms | Windows 10+, macOS 12+, Ubuntu 22.04+ |
| NFR-15 | Installer size | ≤ 150 MB (excluding optional media packs) |
| NFR-16 | Auto-update | Silent background updates with user opt-out capability. |

### 8.5 Security

| ID | Requirement | Target |
|---|---|---|
| NFR-17 | Local-only data | No user data is transmitted off-device without explicit user consent. |
| NFR-18 | API server binding | The FastAPI server binds exclusively to `127.0.0.1` (localhost). |
| NFR-19 | Input sanitization | All search queries are sanitized to prevent SQL injection and XSS. |

---

## 9. Suggested Tech Stack

### 9.1 Technology Overview

| Layer | Technology | Rationale |
|---|---|---|
| **Language (Core)** | Python 3.12+ | Rich ecosystem for NLP, data processing, and rapid prototyping. Type hints and `match` statements improve code quality. |
| **Desktop Shell** | Tauri 2.x (preferred) | Rust-based, smaller binary (~10 MB vs. ~150 MB for Electron), superior performance, native OS integration. Fallback: Electron 28+ if Tauri ecosystem gaps arise. |
| **Frontend Framework** | React 18+ | Industry-standard component model, excellent animation library support, vast ecosystem. Alternative: Next.js if SSR or file-based routing is desired for settings/docs pages. |
| **Styling** | Tailwind CSS 3.x | Utility-first approach enables rapid UI iteration. Custom theme tokens mapped to Tailwind's `extend` config for the Liquid Glass design system. |
| **Animation** | Framer Motion 11+ | Spring-based physics animations, layout animations, gesture support (drag), and `AnimatePresence` for enter/exit transitions. |
| **Advanced Visuals** | WebGL / Three.js (optional) | GPU-accelerated liquid ripple effects, refraction shaders, and particle systems. Enabled only on capable hardware. |
| **API Server** | FastAPI + Uvicorn | Async-first Python web framework with automatic OpenAPI docs. WebSocket support built-in. |
| **Database** | SQLite 3 (via `aiosqlite`) | Lightweight, zero-config, serverless. Ideal for local-first desktop applications. WAL mode for concurrent reads. |
| **Search Data Structures** | Custom Trie, BK-Tree | Trie for O(k) prefix lookup; BK-Tree for O(n^(d/k)) fuzzy matching. Both loaded into memory at startup for maximum speed. |
| **Phonetic Encoding** | `metaphone` / custom Double Metaphone | Maps words to phonetic codes for pronunciation-invariant search. |
| **Speech-to-Text** | OpenAI Whisper (local, `whisper.cpp`) | State-of-the-art local STT model. Runs on CPU (quantized GGML models) for offline voice search. |
| **State Management** | Zustand | Minimal, performant, hook-based state management for React. No boilerplate. |
| **C++ Extensions** | pybind11 | Seamless Python ↔ C++ interop for performance-critical search routines. |
| **Testing** | Pytest, Vitest, Playwright | Pytest for backend unit/integration tests. Vitest for frontend component tests. Playwright for end-to-end UI tests. |
| **Build / Package** | Tauri CLI / electron-builder | Produces native installers (`.msi`, `.dmg`, `.AppImage`) with auto-update support. |

### 9.2 Dependency Summary

```
Backend (Python 3.12+):
├── fastapi >= 0.109
├── uvicorn[standard] >= 0.27
├── aiosqlite >= 0.19
├── pydantic >= 2.5
├── metaphone >= 0.6
├── whisper (openai-whisper) >= 20231117
├── pybind11 >= 2.11 (build dependency)
└── pytest >= 8.0

Frontend (Node.js 20+):
├── react >= 18.2
├── react-dom >= 18.2
├── framer-motion >= 11.0
├── tailwindcss >= 3.4
├── zustand >= 4.5
├── @tauri-apps/api >= 2.0
├── vitest >= 1.2
└── playwright >= 1.41

Desktop Shell:
├── @tauri-apps/cli >= 2.0
└── rust >= 1.75 (Tauri build requirement)
```

---

## 10. Conclusion

### 10.1 Summary

LexiCore is designed to redefine what a desktop dictionary application can be. By combining a high-performance Python data engine with a visually immersive React frontend wrapped in a lightweight Tauri shell, the product delivers:

- **Speed** — Sub-5 ms lookups via in-memory trie, BK-tree, and phonetic indexes.  
- **Intelligence** — Fuzzy matching, phonetic tolerance, and optional AI features ensure users always find what they're looking for.  
- **Beauty** — The Liquid Glass design language, powered by Framer Motion and optional WebGL shaders, creates an interface that feels physical, responsive, and premium.  
- **Learning** — Integrated SRS flashcards transform passive lookup into active vocabulary acquisition.  
- **Privacy** — Fully offline operation with no cloud dependency ensures user data never leaves their machine.

### 10.2 Development Phases

| Phase | Scope | Duration (Est.) |
|---|---|---|
| **Phase 1: Foundation** | Core search engine (trie, BK-tree, phonetic), SQLite data layer, FastAPI server, basic React UI with search and definition display. | 4–5 weeks |
| **Phase 2: Visual Identity** | Liquid Glass design system, Framer Motion animations (morph, autocomplete, glass lighting), dark/light themes. | 3–4 weeks |
| **Phase 3: Learning System** | SRS engine (SM-2), deck management, drag-to-save interaction, export to Anki. | 2–3 weeks |
| **Phase 4: Multimedia & Voice** | Image and audio integration, voice search with Whisper, waveform visualization. | 2–3 weeks |
| **Phase 5: Polish & Packaging** | Performance optimization, C++ extensions, Tauri packaging, installer builds, onboarding tutorial, end-to-end testing. | 2–3 weeks |

**Total estimated timeline: 13–18 weeks.**

### 10.3 Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `backdrop-filter` performance on low-end GPUs | UI jank, dropped frames | Tiered rendering: detect hardware via frame-rate monitoring, disable blur on low-end devices. |
| Whisper model size (~200 MB for base) | Large installer | Ship with quantized `tiny` model (~75 MB); let users download larger models post-install. |
| Tauri ecosystem maturity | Missing platform features | Maintain an Electron fallback; evaluate Tauri 2.x plugin ecosystem quarterly. |
| C++ build complexity | Cross-platform build failures | Keep C++ extensions optional; fall back to pure Python implementations gracefully. |
| Dictionary data licensing | Legal risk | Use freely licensed datasets: WordNet, Wiktionary dumps, CMU Pronouncing Dictionary. |

---

> **Document Status:** Draft v1.0  
> **Next Steps:** Stakeholder review → Architecture validation → Phase 1 sprint planning
