from __future__ import annotations

import difflib
import json
import random
import re
import time
import threading
import urllib.parse
import tkinter as tk
from dataclasses import asdict
from pathlib import Path
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

from .ai import GeminiExplainClient
from .auto_define import auto_define_word
from .benchmark import run_all_benchmarks, run_profile
from .config import DEFAULT_DATA_DIR
from .flashcards import Flashcard, FlashcardStore
from .json_store import load_json, save_json
from .normalization import normalize_word
from .online_lookup import OnlineDictionaryClient
from .sample_data import DEMO_ENTRIES
from .srs import ReviewStore
from .storage import DataFileError, DictionaryStore
from .translation_api import TranslationClient
from .tts import PhoneticsService

VIETNAMESE_CHAR_RE = re.compile(
    r"[àáạảãăằắặẳẵâầấậẩẫèéẹẻẽêềếệểễ"
    r"ìíịỉĩòóọỏõôồốộổỗơờớợởỡ"
    r"ùúụủũưừứựửữỳýỵỷỹđ"
    r"ÀÁẠẢÃĂẰẮẶẲẴÂẦẤẬẨẪÈÉẸẺẼÊỀẾỆỂỄ"
    r"ÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ"
    r"ÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]"
)

DEFAULT_VIETNAMESE_MEANINGS = {
    "algorithm": 'Algorithm; a set of steps to solve a problem.',
    "analysis": 'Analysis; detailed examination of a topic.',
    "binary": 'Binary; a system with two values, usually 0 and 1.',
    "biography": "Biography; an account of a person's life.",
    "biology": 'Biology; the study of living organisms.',
    "biomedical": 'Biomedical; related to biology and medicine.',
    "cache": 'A cache stores data for faster access.',
    "collocation": 'Collocation; words commonly used together.',
    "dictionary": 'Dictionary; a reference for words and their meanings.',
    "frequency": 'Frequency; how often something occurs.',
    "hello": 'Hello.',
    "hi": 'Hi.',
    "memory": 'Memory; storage for data.',
    "nigger": 'A racial slur with severe offensive meaning and should not be used.',
    "pronunciation": 'Pronunciation; how a word is spoken.',
    "review": 'Review; revisit to memorize or evaluate.',
    "trie": 'Trie; a prefix tree data structure.',
    "unicode": 'Unicode; a universal character encoding standard.',
}


class DictionaryAppGUI:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.store = DictionaryStore(self.data_dir)
        self.store.ensure_layout()
        self.store.load_if_available()
        self.review_store = ReviewStore(self.store.paths.review_json)
        self.online_client = OnlineDictionaryClient(self.store.paths.online_cache_json)
        self.ai_client = GeminiExplainClient(self.store.paths.ai_cache_json)
        self.phonetics = PhoneticsService(self.store.paths.phonetic_cache_json, self.store.paths.audio_cache_dir)
        self.flashcard_store = FlashcardStore(self.store.paths.flashcards_json)
        self.translation_client = TranslationClient(self.store.paths.translation_cache_json)
        self.vietnamese_meaning_path = self.data_dir / "vietnamese_meaning.json"
        self.vietnamese_meanings: dict[str, str] = {}
        self._load_vietnamese_meanings()

        self.root = tk.Tk()
        self.root.title("Dictionary — AI Lookup")
        self._app_icon_image: tk.PhotoImage | None = None
        self._apply_window_icon()
        self.root.geometry("1440x900")
        self.root.minsize(1180, 760)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        settings = load_json(
            self.store.paths.ui_settings_json,
            {"theme": "default", "font_size": "100%"},
        )
        self.theme_var = tk.StringVar(value=str(settings.get("theme", "lexicore")))
        self.font_size_var = tk.StringVar(value=str(settings.get("font_size", "100%")))

        self.status_var = tk.StringVar(value='Ready. Search a word to read from the local database.')
        self.stats_var = tk.StringVar()
        self.lookup_word_var = tk.StringVar()
        self.result_word_var = tk.StringVar(value='Dictionary entry')
        self.result_meta_var = tk.StringVar(value='Saved meaning from your local database.')
        self.hint_meta_var = tk.StringVar(value='AI usage hint')
        self.pronounce_meta_var = tk.StringVar(value='Pronunciation cache')
        self.review_word_var = tk.StringVar(value='No words due today')
        self.review_meta_var = tk.StringVar(value='0 due today')
        self.flashcard_word_var = tk.StringVar(value='Flashcards')
        self.flashcard_meta_var = tk.StringVar(value='Load a deck to start practicing.')
        self.flashcard_progress_var = tk.StringVar(value="0 / 0")
        self.flashcard_mode_var = tk.StringVar(value='Due Today')
        self.flashcard_card_hint_var = tk.StringVar(value="")
        self.assistant_meta_var = tk.StringVar(value='Ask for explanations, examples, or study advice.')
        self.hint_question_var = tk.StringVar()
        self.spellcheck_meta_var = tk.StringVar(value='Paste a sentence to auto-fix grammar and analyze.')
        self.spellcheck_corrected_var = tk.StringVar(value='Corrected sentence will appear here.')

        self.display_name = "Yuki"
        self._suggest_timer = None
        self._audio_count_cache: int | None = None
        self._glow_timer = None
        self._suggest_cache: dict[str, list[str]] = {}
        self.current_page = "home"
        self.pages: dict[str, tk.Frame] = {}
        self.nav_buttons: dict[str, tk.Button] = {}
        self.main_shell: tk.Frame | None = None

        self.lookup_meaning_text = 'Search for a word to show the saved definition.'
        self.hint_text = 'Usage guidance will appear here.'
        self.pronounce_text = 'IPA and audio cache details will appear here.'
        self.summary_text = ""
        self.review_text = 'Words due today will appear here.'
        self.bench_output_text = 'Run benchmark or profile to inspect performance.'
        self.assistant_output_text = 'Ask the assistant about vocabulary, usage, grammar, or study tips.'
        self.assistant_question_text = ""
        self.spellcheck_input_text = ""
        self.spellcheck_result_text = 'Enter a sentence and click Check Grammar.'
        self.spellcheck_suggestions_text = 'Error analysis will appear here.'
        self.current_lookup_word = ""
        self.current_lookup_meaning = ""
        self.hint_chat_history: list[tuple[str, str]] = []
        self.hint_quick_questions = [
            'Give me 3 natural examples with this word.',
            'What mistakes should I avoid?',
            'Compare this word with a similar word.',
        ]

        self.flashcard_words: list[str] = []
        self.flashcard_index = 0
        self.flashcard_answer_shown = False
        self.spell_vocabulary: set[str] = set()
        self.spell_candidates: list[str] = []

        self.lookup_entry: tk.Entry | None = None
        self.local_output: ScrolledText | None = None
        self.hint_output: ScrolledText | None = None
        self.hint_question_entry: tk.Entry | None = None
        self.pronounce_output: ScrolledText | None = None
        self.summary_output: ScrolledText | None = None
        self.review_listbox: tk.Listbox | None = None
        self.review_output: ScrolledText | None = None
        self.flashcard_output: tk.Text | None = None
        self.flashcard_card_frame: tk.Frame | None = None
        self.flashcard_content_frame: tk.Frame | None = None
        self.flashcard_transition_job: str | None = None
        self.flashcard_animating = False
        self.assistant_input_widget: ScrolledText | None = None
        self.assistant_output_widget: ScrolledText | None = None
        self.bench_output_widget: ScrolledText | None = None
        self.spellcheck_input_widget: ScrolledText | None = None
        self.spellcheck_output_widget: tk.Text | None = None
        self.spellcheck_suggestions_widget: ScrolledText | None = None

        self._configure_theme()
        self._refresh_spell_vocabulary()
        self._build_layout()
        self._render_summary()
        self._refresh_review_state()
        self._refresh_flashcards(reset=True)
        self._update_stats()
        self.show_page(self.current_page)

    def _apply_window_icon(self) -> None:
        icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
        if not icon_path.exists():
            return
        try:
            self._app_icon_image = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, self._app_icon_image)
        except Exception:
            self._app_icon_image = None

    def _load_vietnamese_meanings(self) -> None:
        payload = load_json(self.vietnamese_meaning_path, {})
        normalized: dict[str, str] = {}
        if isinstance(payload, dict):
            for raw_word, raw_meaning in payload.items():
                word_key = normalize_word(str(raw_word))
                meaning_text = " ".join(str(raw_meaning or "").split()).strip()
                if word_key and meaning_text:
                    normalized[word_key] = meaning_text
        changed = False
        for word_key, meaning_text in DEFAULT_VIETNAMESE_MEANINGS.items():
            if word_key not in normalized:
                normalized[word_key] = meaning_text
                changed = True
        if changed or not self.vietnamese_meaning_path.exists():
            save_json(self.vietnamese_meaning_path, normalized)
        self.vietnamese_meanings = normalized

    def _configure_theme(self) -> None:
        palette_name = self.theme_var.get()
        palettes = {
            "default": {
                "bg": "#0b0e1a",
                "surface": "#151a2e",
                "surface_alt": "#1a2038",
                "header": "#0f1326",
                "primary": "#7c5cfc",
                "primary_dark": "#5a3ec8",
                "accent": "#ef4444",
                "accent_alt": "#f59e0b",
                "text": "#e8eaf0",
                "muted": "#6b7294",
                "line": "#2a2f4a",
                "hero": "#0f1322",
                "hero_line": "#2a2f4a",
                "nav_active": "#7c5cfc",
                "nav_hover": "#1e2444",
                "glow1": "#7c5cfc",
                "glow2": "#3b82f6",
                "glow3": "#ec4899",
            },
            "blue white": {
                "bg": "#eef3fb",
                "surface": "#ffffff",
                "surface_alt": "#f7f9fd",
                "header": "#0d2f6f",
                "primary": "#0f52ba",
                "primary_dark": "#08285e",
                "accent": "#cf3f3f",
                "accent_alt": "#c48a1d",
                "text": "#15233b",
                "muted": "#5a6b84",
                "line": "#d6deed",
                "hero": "#f4f8ff",
                "hero_line": "#b8ccef",
            },
            "black_white": {
                "bg": "#060735",
                "surface": "#253766",
                "surface_alt": "#304577",
                "header": "#050528",
                "primary": "#4a6bff",
                "primary_dark": "#22357f",
                "accent": "#3958d8",
                "accent_alt": "#2c3b6d",
                "text": "#f8f9ff",
                "muted": "#b7c0e3",
                "line": "#41538f",
                "hero": "#090c3a",
                "hero_line": "#445798",
            },
            "black_gold": {
                "bg": "#151515",
                "surface": "#1d1d1d",
                "surface_alt": "#252525",
                "header": "#090909",
                "primary": "#d4af37",
                "primary_dark": "#9b7b16",
                "accent": "#f0c94d",
                "accent_alt": "#3b3b3b",
                "text": "#f5e8b8",
                "muted": "#c7b570",
                "line": "#51431e",
                "hero": "#211b0e",
                "hero_line": "#7b651f",
            },
        }
        self.colors = palettes.get(palette_name, palettes["default"])
        self._is_lexicore = palette_name == "default"

        scale_lookup = {"90%": 0.9, "100%": 1.0, "115%": 1.15, "130%": 1.3}
        scale = scale_lookup.get(self.font_size_var.get(), 1.0)

        def size(value: int) -> int:
            return max(8, int(round(value * scale)))

        self.fonts = {
            "brand": ("Segoe UI Semibold", size(24), "bold"),
            "headline": ("Segoe UI", size(28), "bold"),
            "word": ("Segoe UI Semibold", size(26), "bold"),
            "title": ("Segoe UI Semibold", size(15)),
            "subtitle": ("Segoe UI", size(10)),
            "body": ("Segoe UI", size(11)),
            "button": ("Segoe UI Semibold", size(10)),
            "review_word": ("Segoe UI Semibold", size(24), "bold"),
            "flash_word": ("Segoe UI Semibold", size(30), "bold"),
            "flash_meaning": ("Segoe UI", size(16)),
            "flash_title": ("Segoe UI Semibold", size(17)),
            "greeting": ("Segoe UI", size(32), "bold"),
            "nav_item": ("Segoe UI", size(11)),
            "nav_item_active": ("Segoe UI Semibold", size(11)),
            "wotd_word": ("Segoe UI Semibold", size(22), "bold"),
            "wotd_label": ("Segoe UI", size(9)),
            "status_card": ("Segoe UI", size(9)),
        }
        if palette_name in ("black_white", "default"):
            self.flash_colors = {
                "bg": self.colors["bg"],
                "panel": self.colors["surface"],
                "panel_alt": self.colors["surface_alt"],
                "card": self.colors.get("nav_hover", self.colors["surface"]),
                "accent": self.colors["primary"],
                "accent_dark": self.colors["primary_dark"],
                "text": self.colors["text"],
                "muted": self.colors["muted"],
                "line": self.colors["line"],
            }
        else:
            self.flash_colors = {
                "bg": "#eef3fb",
                "panel": "#1f3f8f",
                "panel_alt": "#ffffff",
                "card": "#ffffff",
                "accent": "#2f6fff",
                "accent_dark": "#2348b8",
                "text": "#14284f",
                "muted": "#5f7194",
                "line": "#c7d6ef",
            }
        self.root.configure(bg=self.colors["bg"])

    def _build_layout(self) -> None:
        if self.main_shell is not None:
            self.main_shell.destroy()

        self.main_shell = tk.Frame(self.root, bg=self.colors["bg"])
        self.main_shell.pack(fill="both", expand=True)

        # --- Background glow canvas (lexicore theme only) ---
        if self._is_lexicore:
            self._bg_canvas = tk.Canvas(self.main_shell, bg=self.colors["bg"], highlightthickness=0)
            self._bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
            self._bg_canvas.bind("<Configure>", self._draw_bg_glows)

        workspace = tk.Frame(self.main_shell, bg=self.colors["bg"])
        workspace.pack(fill="both", expand=True)

        self._build_header(workspace)

        page_shell = tk.Frame(workspace, bg=self.colors["bg"], padx=24, pady=20)
        page_shell.pack(side="left", fill="both", expand=True)
        self._build_pages(page_shell)
        self._build_statusbar(self.main_shell)
        self._restore_panels()

    def _draw_bg_glows(self, event=None) -> None:
        """Draw soft glowing color circles on the background canvas (debounced)."""
        if self._glow_timer is not None:
            try:
                self.root.after_cancel(self._glow_timer)
            except Exception:
                pass
        self._glow_timer = self.root.after(150, self._draw_bg_glows_now)

    def _draw_bg_glows_now(self) -> None:
        """Actually draw the glow circles."""
        self._glow_timer = None
        canvas = getattr(self, "_bg_canvas", None)
        if canvas is None:
            return
        canvas.delete("glow")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 10:
            return
        # Purple glow - top left area
        self._draw_glow_circle(canvas, int(w * 0.18), int(h * 0.22), 320, "#2a1a5e", 0.35)
        # Blue glow - center right
        self._draw_glow_circle(canvas, int(w * 0.72), int(h * 0.35), 280, "#0f2a5e", 0.30)
        # Pink glow - bottom center
        self._draw_glow_circle(canvas, int(w * 0.5), int(h * 0.82), 250, "#3a1040", 0.25)
        # Subtle cyan glow - top right
        self._draw_glow_circle(canvas, int(w * 0.85), int(h * 0.15), 200, "#0a2a3a", 0.20)

    def _draw_glow_circle(self, canvas: tk.Canvas, cx: int, cy: int, radius: int, color: str, alpha: float) -> None:
        """Draw a series of concentric translucent ovals to simulate a soft glow."""
        steps = 8
        for i in range(steps):
            ratio = (steps - i) / steps
            r = int(radius * ratio)
            if r < 5:
                continue
            r_hex = int(int(color[1:3], 16) * ratio)
            g_hex = int(int(color[3:5], 16) * ratio)
            b_hex = int(int(color[5:7], 16) * ratio)
            fill = f"#{r_hex:02x}{g_hex:02x}{b_hex:02x}"
            canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=fill, outline="", tags="glow",
            )

    def _build_header(self, parent: tk.Frame) -> None:
        sidebar_bg = self.colors["header"]
        sidebar_border = self.colors["line"]
        header = tk.Frame(parent, bg=sidebar_bg, padx=16, pady=16, width=240,
                          highlightthickness=1, highlightbackground=sidebar_border)
        header.pack(side="left", fill="y")
        header.pack_propagate(False)

        # --- Brand ---
        brand = tk.Frame(header, bg=sidebar_bg)
        brand.pack(fill="x")
        tk.Label(brand, text='✦ Dictionary', bg=sidebar_bg, fg=self.colors["text"],
                 font=self.fonts["brand"]).pack(anchor="w")
        tk.Label(brand, text='AI-powered word lookup',
                 bg=sidebar_bg, fg=self.colors["muted"], font=self.fonts["subtitle"],
                 justify="left", wraplength=210).pack(anchor="w", pady=(2, 0))

        # --- Separator ---
        tk.Frame(header, bg=sidebar_border, height=1).pack(fill="x", pady=(14, 14))

        # --- Navigation ---
        nav = tk.Frame(header, bg=sidebar_bg)
        nav.pack(fill="x")
        nav_items = [
            ("home", "🏠", 'Home'),
            ("review", "📋", 'Saved Words'),
            ("flashcards", "🃏", 'Flashcards'),
            ("spellcheck", "✍️", 'Grammar'),
            ("assistant", "🤖", 'Assistant'),
        ]
        for page_id, icon, label in nav_items:
            btn_bg = sidebar_bg
            btn_font = self.fonts["nav_item"]
            button = tk.Button(
                nav,
                text=f"  {icon}  {label}",
                relief="flat",
                bd=0,
                padx=14,
                pady=9,
                bg=btn_bg,
                fg=self.colors["text"],
                activebackground=self.colors.get("nav_hover", self.colors["primary_dark"]),
                activeforeground="white",
                font=btn_font,
                anchor="w",
                cursor="hand2",
                command=lambda target=page_id: self.show_page(target),
            )
            button.pack(fill="x", pady=2)
            self.nav_buttons[page_id] = button

        # --- Spacer to push settings and status card to bottom ---
        spacer = tk.Frame(header, bg=sidebar_bg)
        spacer.pack(fill="both", expand=True)

        # --- Settings area ---
        settings = tk.Frame(header, bg=sidebar_bg)
        settings.pack(fill="x", pady=(8, 0))

        tk.Frame(header, bg=sidebar_border, height=1).pack(fill="x", pady=(8, 8))

        self._header_label(settings, 'Theme').pack(anchor="w")
        self._option_menu(settings, self.theme_var,
                          ["default", "blue white"],
                          self.apply_ui_preferences).pack(fill="x", pady=(4, 8))
        self._header_label(settings, 'Font').pack(anchor="w")
        self._option_menu(settings, self.font_size_var,
                          ["90%", "100%", "115%", "130%"],
                          self.apply_ui_preferences).pack(fill="x", pady=(4, 8))

        btn_row = tk.Frame(settings, bg=sidebar_bg)
        btn_row.pack(fill="x", pady=(4, 0))
        self._action_button(btn_row, '⟳ Reload', self.reload_data, self.colors["primary"]).pack(side="left", fill="x", expand=True)
        self._action_button(btn_row, '★ Demo', self.init_demo, self.colors["primary_dark"]).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # --- Status card at bottom ---
        tk.Frame(header, bg=sidebar_border, height=1).pack(fill="x", pady=(10, 8))
        status_card = tk.Frame(header, bg=self.colors.get("nav_hover", sidebar_bg), padx=10, pady=8,
                               highlightthickness=1, highlightbackground=sidebar_border)
        status_card.pack(fill="x")
        entry_count = len(self.store.all_words())
        tk.Label(status_card, text=f"📚 {entry_count:,} words loaded",
                 bg=self.colors.get("nav_hover", sidebar_bg), fg=self.colors["text"],
                 font=self.fonts["status_card"]).pack(anchor="w")
        tk.Label(status_card, text=f"🎯 {len(self.review_store.due_items())} due today",
                 bg=self.colors.get("nav_hover", sidebar_bg), fg=self.colors["muted"],
                 font=self.fonts["status_card"]).pack(anchor="w", pady=(2, 0))

    def _build_pages(self, parent: tk.Frame) -> None:
        self.pages = {
            "home": tk.Frame(parent, bg=self.colors["bg"]),
            "review": tk.Frame(parent, bg=self.colors["bg"]),
            "flashcards": tk.Frame(parent, bg=self.colors["bg"]),
            "spellcheck": tk.Frame(parent, bg=self.colors["bg"]),
            "assistant": tk.Frame(parent, bg=self.colors["bg"]),
            "benchmark": tk.Frame(parent, bg=self.colors["bg"]),
        }
        for frame in self.pages.values():
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_home_page(self.pages["home"])
        self._build_review_page(self.pages["review"])
        self._build_flashcards_page(self.pages["flashcards"])
        self._build_spellcheck_page(self.pages["spellcheck"])
        self._build_assistant_page(self.pages["assistant"])
        self._build_benchmark_page(self.pages["benchmark"])

    def _build_statusbar(self, parent: tk.Frame) -> None:
        bar = tk.Frame(parent, bg=self.colors["hero"], padx=20, pady=8,
                       highlightthickness=1, highlightbackground=self.colors["line"])
        bar.pack(fill="x")
        tk.Label(bar, textvariable=self.status_var, bg=self.colors["hero"],
                 fg=self.colors["muted"], font=self.fonts["subtitle"]).pack(side="left")
        tk.Label(bar, textvariable=self.stats_var, bg=self.colors["hero"],
                 fg=self.colors["muted"], font=self.fonts["subtitle"]).pack(side="right")


    def _build_home_page(self, parent: tk.Frame) -> None:
        """ChatGPT-style Home with autocomplete, meaning display, and audio."""
        # --- Top area: welcome + search (will slide up when results shown) ---
        self._home_top = tk.Frame(parent, bg=self.colors["bg"])
        self._home_top.place(relx=0.5, rely=0.30, anchor="center", relwidth=0.7)

        # Welcome text
        self._home_greeting = tk.Label(
            self._home_top,
            text="What can I look up for you?",
            bg=self.colors["bg"],
            fg=self.colors["text"],
            font=("Segoe UI", 26),
        )
        self._home_greeting.pack(anchor="center", pady=(0, 30))

        # --- Search bar ---
        search_bar = tk.Frame(
            self._home_top,
            bg=self.colors["surface"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=16,
            pady=6,
        )
        search_bar.pack(fill="x", padx=10)

        self._home_entry = tk.Entry(
            search_bar,
            textvariable=self.lookup_word_var,
            relief="flat",
            bd=0,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 14),
            insertbackground=self.colors["text"],
            width=45,
        )
        self._home_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(4, 0))
        self._home_entry.bind("<Return>", lambda _e: self._home_do_lookup())
        self._home_entry.bind("<KeyRelease>", self._home_on_key)
        self._home_entry.bind("<Down>", self._home_suggest_down)
        self._home_entry.bind("<Up>", self._home_suggest_up)

        send_btn = tk.Button(
            search_bar,
            text="\u27a4",
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            bg=self.colors["primary"],
            fg="white",
            activebackground=self.colors["primary_dark"],
            activeforeground="white",
            font=("Segoe UI Semibold", 13),
            cursor="hand2",
            command=self._home_do_lookup,
        )
        send_btn.pack(side="right", padx=(8, 2))

        # --- Autocomplete suggestion listbox ---
        self._home_suggest_frame = tk.Frame(
            self._home_top,
            bg=self.colors["surface"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
        )
        # Not packed yet — shown dynamically

        self._home_suggest_listbox = tk.Listbox(
            self._home_suggest_frame,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Segoe UI", 12),
            relief="flat",
            bd=0,
            selectbackground=self.colors["primary"],
            selectforeground="white",
            activestyle="none",
            height=6,
            cursor="hand2",
            highlightthickness=0,
        )
        self._home_suggest_listbox.pack(fill="both", expand=True, padx=4, pady=4)
        self._home_suggest_listbox.bind("<<ListboxSelect>>", self._home_suggest_select)
        self._home_suggest_visible = False

        # --- Results area (hidden initially) ---
        self._home_results = tk.Frame(parent, bg=self.colors["bg"])
        # placed below the top area, initially hidden

        # -- Result word display --
        self._home_result_word = tk.StringVar(value="")
        self._home_result_meta = tk.StringVar(value="")

        result_header = tk.Frame(self._home_results, bg=self.colors["surface"],
                                  padx=20, pady=14,
                                  highlightthickness=1, highlightbackground=self.colors["line"])
        result_header.pack(fill="x", padx=10, pady=(0, 0))

        word_row = tk.Frame(result_header, bg=self.colors["surface"])
        word_row.pack(fill="x")
        tk.Label(word_row, textvariable=self._home_result_word,
                 bg=self.colors["surface"], fg=self.colors["text"],
                 font=("Segoe UI Semibold", 22, "bold")).pack(side="left")
        tk.Label(word_row, textvariable=self._home_result_meta,
                 bg=self.colors["surface"], fg=self.colors["muted"],
                 font=self.fonts["subtitle"]).pack(side="left", padx=(12, 0))

        # Audio buttons row
        audio_row = tk.Frame(result_header, bg=self.colors["surface"])
        audio_row.pack(fill="x", pady=(10, 0))
        self._action_button(audio_row, "\u25b6 Play",
                            self.generate_pronunciation_audio, self.colors["primary"]).pack(side="left")
        self._action_button(audio_row, "\u2b50 Save to Review",
                            self.schedule_current_word, self.colors.get("accent_alt", "#f59e0b")).pack(side="right")

        # -- Meaning block --
        meaning_card = tk.Frame(self._home_results, bg=self.colors["surface"],
                                 padx=20, pady=14,
                                 highlightthickness=1, highlightbackground=self.colors["line"])
        meaning_card.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        meaning_cols = tk.Frame(meaning_card, bg=self.colors["surface"])
        meaning_cols.pack(fill="both", expand=True)
        meaning_cols.grid_columnconfigure(0, weight=6)
        meaning_cols.grid_columnconfigure(1, weight=4)
        meaning_cols.grid_rowconfigure(0, weight=1)

        # Left: English meaning
        left = tk.Frame(meaning_cols, bg=self.colors["surface"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(left, text="Meaning", bg=self.colors["surface"],
                 fg=self.colors["text"], font=self.fonts["title"]).pack(anchor="w")
        self._home_meaning_output = self._text_panel(left, height=12)
        self._home_meaning_output.pack(fill="both", expand=True, pady=(8, 0))

        # Right: Vietnamese meaning
        right = tk.Frame(meaning_cols, bg=self.colors["surface"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(right, text="Vietnamese", bg=self.colors["surface"],
                 fg=self.colors["text"], font=self.fonts["title"]).pack(anchor="w")
        self._home_vn_output = self._text_panel(right, height=12)
        self._home_vn_output.pack(fill="both", expand=True, pady=(8, 0))

        self._home_results_visible = False

    # --- Home autocomplete logic (online + local) ---
    def _home_on_key(self, event=None) -> None:
        """Show local suggestions instantly; debounce online fetch."""
        typed = self.lookup_word_var.get().strip().lower()
        if not typed:
            self._home_hide_suggestions()
            return

        # Check merged cache first (includes online results from earlier)
        if typed in self._suggest_cache:
            self._home_show_suggestions(self._suggest_cache[typed])
        else:
            # Show local trie matches immediately — no debounce needed
            local = self.store.prefix_trie(typed, limit=8)
            if local:
                self._home_show_suggestions(local)
            else:
                self._home_hide_suggestions()

        # Debounce the online fetch (400ms) to avoid spamming the API
        if self._suggest_timer is not None:
            try:
                self.root.after_cancel(self._suggest_timer)
            except Exception:
                pass
        self._suggest_timer = self.root.after(400, self._home_fetch_online_suggestions)

    def _home_fetch_online_suggestions(self) -> None:
        """Fetch suggestions from online API in background thread."""
        typed = self.lookup_word_var.get().strip().lower()
        if not typed:
            return

        # Already have merged results cached
        if typed in self._suggest_cache:
            return

        local = self.store.prefix_trie(typed, limit=8)

        # Fetch online suggestions in background thread
        def fetch():
            try:
                import urllib.request, json as _json
                url = f"https://api.datamuse.com/sug?s={urllib.parse.quote(typed)}&max=8"
                req = urllib.request.Request(url, headers={"User-Agent": "LexiCore/1.0"})
                with urllib.request.urlopen(req, timeout=2) as resp:
                    data = _json.loads(resp.read().decode("utf-8"))
                online_words = [item["word"] for item in data if "word" in item][:8]
                # Merge local + online, deduplicate
                seen = set()
                merged = []
                for w in local + online_words:
                    key = w.lower()
                    if key not in seen:
                        seen.add(key)
                        merged.append(w)
                merged = merged[:8]
                self._suggest_cache[typed] = merged
                # Update UI from main thread
                self.root.after(0, lambda: self._home_update_suggestions(typed, merged))
            except Exception:
                pass  # Silently fall back to local results

        threading.Thread(target=fetch, daemon=True).start()

    def _home_update_suggestions(self, typed: str, words: list) -> None:
        """Update suggestion list on main thread if input hasn't changed."""
        current = self.lookup_word_var.get().strip().lower()
        if current == typed and words:
            self._home_show_suggestions(words)

    def _home_show_suggestions(self, words: list) -> None:
        """Display the autocomplete dropdown."""
        self._home_suggest_listbox.delete(0, tk.END)
        for w in words:
            self._home_suggest_listbox.insert(tk.END, self._uppercase_first_character(w))
        if not self._home_suggest_visible:
            self._home_suggest_frame.pack(fill="x", padx=10, pady=(2, 0))
            self._home_suggest_visible = True

    def _home_hide_suggestions(self) -> None:
        """Hide the autocomplete dropdown."""
        if self._home_suggest_visible:
            self._home_suggest_frame.pack_forget()
            self._home_suggest_visible = False

    def _home_suggest_select(self, event=None) -> None:
        """When user clicks a suggestion, fill the entry and lookup."""
        sel = self._home_suggest_listbox.curselection()
        if not sel:
            return
        word = self._home_suggest_listbox.get(sel[0]).strip()
        self.lookup_word_var.set(word)
        self._home_hide_suggestions()
        self._home_do_lookup()

    def _home_suggest_down(self, event=None) -> None:
        """Move selection down in suggestion list."""
        if not self._home_suggest_visible:
            return
        cur = self._home_suggest_listbox.curselection()
        size = self._home_suggest_listbox.size()
        if not cur:
            self._home_suggest_listbox.selection_set(0)
        elif cur[0] < size - 1:
            self._home_suggest_listbox.selection_clear(cur[0])
            self._home_suggest_listbox.selection_set(cur[0] + 1)

    def _home_suggest_up(self, event=None) -> None:
        """Move selection up in suggestion list."""
        if not self._home_suggest_visible:
            return
        cur = self._home_suggest_listbox.curselection()
        if cur and cur[0] > 0:
            self._home_suggest_listbox.selection_clear(cur[0])
            self._home_suggest_listbox.selection_set(cur[0] - 1)

    # --- Home lookup ---
    def _home_do_lookup(self) -> None:
        """Perform lookup and show results on the Home page."""
        self._home_hide_suggestions()
        word = self.lookup_word_var.get().strip()
        if not word:
            return
        # Use the existing lookup logic
        self.lookup_word()
        # Now display results on Home page
        self._home_show_results()

    def _home_show_results(self) -> None:
        """Display lookup results on the Home page."""
        if not self.current_lookup_word:
            return
        # Slide the welcome text up and show results
        self._home_greeting.configure(font=("Segoe UI", 18))
        self._home_top.place_configure(rely=0.12)

        # Set result data
        self._home_result_word.set(self._uppercase_first_character(self.current_lookup_word))
        self._home_result_meta.set(f"from local database")

        # Write meaning
        self._write_text(self._home_meaning_output, self.lookup_meaning_text)

        # Write Vietnamese
        vn = self._get_vietnamese_meaning_from_database(self.current_lookup_word)
        self._write_text(self._home_vn_output, vn or "No Vietnamese meaning available.")

        # Show the results area
        if not self._home_results_visible:
            self._home_results.place(relx=0.5, rely=0.52, anchor="center", relwidth=0.7, relheight=0.55)
            self._home_results_visible = True

    def _home_search(self) -> None:
        """Navigate to search page and trigger lookup."""
        self.show_page("search")
        self.lookup_word()

    def _home_lookup(self, word: str) -> None:
        """Set word and navigate to search page."""
        self.lookup_word_var.set(word)
        self.show_page("search")
        self.lookup_word()

    def _build_search_page(self, parent: tk.Frame) -> None:
        hero = tk.Frame(
            parent,
            bg=self.colors["hero"],
            highlightthickness=1,
            highlightbackground=self.colors["hero_line"],
            padx=24,
            pady=22,
        )
        hero.pack(fill="x", pady=(0, 20))

        top = tk.Frame(hero, bg=self.colors["hero"])
        top.pack(fill="x")
        copy = tk.Frame(top, bg=self.colors["hero"])
        copy.pack(side="left", fill="x", expand=True)
        tk.Label(copy, text='English Dictionary', bg=self.colors["hero"], fg=self.colors["text"], font=self.fonts["title"]).pack(anchor="w")
        tk.Label(
            copy,
            text='Pronounce words, get AI usage guidance, and keep everything saved in your local study database.',
            bg=self.colors["hero"],
            fg=self.colors["muted"],
            font=self.fonts["subtitle"],
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        search_shell = tk.Frame(hero, bg=self.colors["surface"], padx=14, pady=14)
        search_shell.pack(fill="x", pady=(18, 0))
        self.lookup_entry = tk.Entry(
            search_shell,
            textvariable=self.lookup_word_var,
            relief="flat",
            bd=0,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=self.fonts["headline"],
            insertbackground=self.colors["text"],
        )
        self.lookup_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(6, 12))
        self.lookup_entry.bind("<Return>", lambda _event: self.lookup_word())
        self._action_button(search_shell, "Tra", self.lookup_word, self.colors["primary"]).pack(side="left")

        body = tk.Frame(parent, bg=self.colors["bg"])
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=7)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        local_card = self._card(body)
        local_card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        tk.Label(local_card, text='Meaning', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["title"]).pack(anchor="w")
        tk.Label(local_card, textvariable=self.result_word_var, bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["word"]).pack(
            anchor="w"
        )
        tk.Label(local_card, textvariable=self.result_meta_var, bg=self.colors["surface"], fg=self.colors["muted"], font=self.fonts["subtitle"]).pack(
            anchor="w", pady=(4, 0)
        )
        meaning_actions = tk.Frame(local_card, bg=self.colors["surface"])
        meaning_actions.pack(fill="x", pady=(12, 0))
        self._action_button(meaning_actions, 'Add To Review', self.schedule_current_word, self.colors["accent_alt"]).pack(side="left")
        self._action_button(meaning_actions, 'Open Flashcard', self.open_current_flashcard, self.colors["primary"]).pack(side="left", padx=8)
        self.local_output = self._text_panel(local_card, height=22)
        self.local_output.pack(fill="both", expand=True, pady=(14, 0))

        side = tk.Frame(body, bg=self.colors["bg"])
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_rowconfigure(0, weight=3)
        side.grid_rowconfigure(1, weight=3)

        summary_card = self._card(side)
        summary_card.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        tk.Label(summary_card, text='Vietnamese Meaning', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["title"]).pack(
            anchor="w"
        )
        self.summary_output = self._text_panel(summary_card, height=10)
        self.summary_output.pack(fill="both", expand=True, pady=(12, 0))

        pronounce_card = self._card(side)
        pronounce_card.grid(row=1, column=0, sticky="nsew")
        tk.Label(pronounce_card, text='Pronounce', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["title"]).pack(
            anchor="w"
        )
        tk.Label(pronounce_card, textvariable=self.pronounce_meta_var, bg=self.colors["surface"], fg=self.colors["muted"], font=self.fonts["subtitle"]).pack(
            anchor="w", pady=(4, 0)
        )
        pronounce_actions = tk.Frame(pronounce_card, bg=self.colors["surface"])
        pronounce_actions.pack(fill="x", pady=(12, 0))
        self._action_button(pronounce_actions, 'Generate + Play', self.generate_pronunciation_audio, self.colors["primary"]).pack(side="left")
        self._action_button(pronounce_actions, 'Play', self.play_pronunciation_audio, self.colors["accent_alt"]).pack(side="left", padx=8)
        self._action_button(pronounce_actions, 'Stop', self.stop_pronunciation_audio, self.colors["accent"]).pack(side="left")
        self.pronounce_output = self._text_panel(pronounce_card, height=8)
        self.pronounce_output.pack(fill="both", expand=True, pady=(12, 0))

    def _build_review_page(self, parent: tk.Frame) -> None:
        shell = self._card(parent)
        shell.pack(fill="both", expand=True)
        shell.grid_columnconfigure(0, weight=3)
        shell.grid_columnconfigure(1, weight=7)
        shell.grid_rowconfigure(0, weight=1)

        # --- Left panel: due list ---
        list_panel = tk.Frame(shell, bg=self.colors["surface"])
        list_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        tk.Label(
            list_panel,
            text='📋 Due Today',
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=self.fonts["flash_title"],
        ).pack(anchor="w")
        tk.Label(
            list_panel,
            textvariable=self.review_meta_var,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=self.fonts["subtitle"],
        ).pack(anchor="w", pady=(4, 10))
        self.review_listbox = tk.Listbox(
            list_panel,
            relief="flat",
            bd=0,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            selectbackground=self.colors["primary"],
            selectforeground="white",
            font=self.fonts["body"],
            activestyle="none",
        )
        self.review_listbox.pack(fill="both", expand=True)
        self.review_listbox.bind("<<ListboxSelect>>", self._select_review_item)

        # --- Right panel: review card ---
        detail_panel = tk.Frame(shell, bg=self.colors["surface"])
        detail_panel.grid(row=0, column=1, sticky="nsew")

        # Controls bar
        controls = tk.Frame(detail_panel, bg=self.colors["surface"])
        controls.pack(fill="x")
        tk.Label(
            controls,
            text='📖 Review',
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=self.fonts["flash_title"],
        ).pack(side="left")
        review_actions = [
            ('✔ Remember', lambda: self.review_current(True), self.colors["primary"]),
            ('↻ Again', lambda: self.review_current(False), self.colors["surface_alt"]),
            ('⟳ Refresh', self._refresh_review_state, self.colors["surface_alt"]),
        ]
        for idx, (text, cmd, color) in enumerate(review_actions):
            self._action_button(controls, text, cmd, color).pack(side="left", padx=(10 if idx == 0 else 6, 0))

        # Card stage
        stage = tk.Frame(detail_panel, bg=self.colors["surface"])
        stage.pack(fill="both", expand=True, pady=(14, 0))

        card = tk.Frame(
            stage,
            bg=self.colors["surface_alt"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
        )
        card.place(relx=0.5, rely=0.52, relwidth=0.95, relheight=0.9, anchor="center")

        card_content = tk.Frame(card, bg=self.colors["surface_alt"], padx=20, pady=18)
        card_content.place(x=0, y=0, relwidth=1, relheight=1)

        # Word on top (centered, large)
        tk.Label(
            card_content,
            textvariable=self.review_word_var,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            font=self.fonts["flash_word"],
            anchor="center",
        ).pack(anchor="center", pady=(8, 12))

        # Scrollable text panel below
        self.review_output = self._text_panel(card_content, height=14)
        self.review_output.configure(
            wrap="word",
            font=self.fonts["flash_meaning"],
        )
        self.review_output.pack(fill="both", expand=True)

    def _build_flashcards_page(self, parent: tk.Frame) -> None:
        shell = self._card(parent)
        shell.pack(fill="both", expand=True)

        top_bar = tk.Frame(shell, bg=self.colors["surface"])
        top_bar.pack(fill="x")
        title_wrap = tk.Frame(top_bar, bg=self.colors["surface"])
        title_wrap.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_wrap,
            text='📚 Flashcards Studio',
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=self.fonts["flash_title"],
        ).pack(anchor="w")
        tk.Label(
            title_wrap,
            textvariable=self.flashcard_meta_var,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=self.fonts["subtitle"],
        ).pack(anchor="w", pady=(4, 0))
        tk.Label(
            top_bar,
            textvariable=self.flashcard_progress_var,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=self.fonts["title"],
        ).pack(side="right", padx=(10, 0))

        controls = tk.Frame(shell, bg=self.colors["surface"])
        controls.pack(fill="x", pady=(10, 0))
        tk.Label(
            controls,
            text="\U0001F393",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=self.fonts["title"],
        ).pack(side="left", padx=(0, 6))
        mode_menu = self._option_menu(controls, self.flashcard_mode_var, ['Due Today', 'All Words', 'Custom Cards'], self._change_flashcard_mode)
        mode_menu.configure(
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            activebackground=self.colors["primary"],
            activeforeground="white",
        )
        mode_menu["menu"].configure(
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            activebackground=self.colors["primary"],
            activeforeground="white",
        )
        mode_menu.pack(side="left")
        actions = [
            ('⬇ Load', lambda: self._refresh_flashcards(reset=True), self.colors["primary"]),
            ('⟳ Shuffle', self.shuffle_flashcards, self.colors["surface_alt"]),
            ('🎯 Match', self._match_flashcards, self.colors["surface_alt"]),
            ('❓ Quiz', self._quiz_flashcards, self.colors["surface_alt"]),
            ('➕ Add', self.create_flashcard, self.colors["primary_dark"]),
            ('✎ Edit', self.edit_current_flashcard, self.colors["primary_dark"]),
            ('✖ Delete', self.delete_current_flashcard, self.colors["accent"]),
            ('💾 Save', self.save_current_word_as_flashcard, self.colors["primary_dark"]),
            ('✔ Remember', lambda: self.mark_flashcard(True), self.colors["primary_dark"]),
            ('↻ Again', lambda: self.mark_flashcard(False), self.colors["surface_alt"]),
            ('🔊 Audio', self.play_flashcard_audio, self.colors["surface_alt"]),
        ]
        for index, (text, command, color) in enumerate(actions):
            self._action_button(controls, text, command, color).pack(side="left", padx=(8 if index == 0 else 6, 0))

        stage = tk.Frame(shell, bg=self.colors["surface"])
        stage.pack(fill="both", expand=True, pady=(14, 0))

        card = tk.Frame(
            stage,
            bg=self.colors["surface_alt"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
        )
        card.place(relx=0.5, rely=0.52, relwidth=0.9, relheight=0.86, anchor="center")
        self.flashcard_card_frame = card

        content = tk.Frame(card, bg=self.colors["surface_alt"], padx=20, pady=18)
        content.place(x=0, y=0, relwidth=1, relheight=1)
        self.flashcard_content_frame = content

        tk.Label(
            content,
            textvariable=self.flashcard_word_var,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            font=self.fonts["flash_word"],
            anchor="center",
        ).pack(anchor="center", pady=(8, 12))

        self.flashcard_output = self._text_panel(content, height=14)
        self.flashcard_output.configure(
            wrap="word",
            font=self.fonts["flash_meaning"],
        )
        self.flashcard_output.pack(fill="both", expand=True)
        self._bind_flashcard_click_targets(card)

    def _build_spellcheck_page(self, parent: tk.Frame) -> None:
        shell = self._card(parent)
        shell.pack(fill="both", expand=True)

        tk.Label(shell, text='Grammar Fix', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["title"]).pack(
            anchor="w"
        )
        tk.Label(shell, textvariable=self.spellcheck_meta_var, bg=self.colors["surface"], fg=self.colors["muted"], font=self.fonts["subtitle"]).pack(
            anchor="w", pady=(4, 10)
        )

        self.spellcheck_input_widget = self._text_panel(shell, height=5)
        self.spellcheck_input_widget.pack(fill="x")
        action_row = tk.Frame(shell, bg=self.colors["surface"])
        action_row.pack(fill="x", pady=(10, 0))
        self._action_button(action_row, 'Check Grammar', self.check_sentence_spelling, self.colors["primary"]).pack(side="left")
        self._action_button(action_row, 'Load Example', self.load_spellcheck_example, self.colors["accent_alt"]).pack(side="left", padx=8)
        self._action_button(action_row, 'Clear', self.clear_spellcheck, self.colors["accent"]).pack(side="left")

        result_shell = tk.Frame(shell, bg=self.colors["surface"])
        result_shell.pack(fill="both", expand=True, pady=(12, 0))
        tk.Label(result_shell, text='Highlighted Sentence', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["subtitle"]).pack(
            anchor="w"
        )
        self.spellcheck_output_widget = tk.Text(
            result_shell,
            wrap="word",
            height=7,
            relief="flat",
            bd=0,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            font=self.fonts["body"],
            padx=12,
            pady=12,
        )
        self.spellcheck_output_widget.pack(fill="x", pady=(6, 10))
        self.spellcheck_output_widget.tag_configure("error", foreground="#cf3f3f", underline=1)
        self.spellcheck_output_widget.configure(state="disabled")

        tk.Label(result_shell, text='Corrected Sentence', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["subtitle"]).pack(
            anchor="w"
        )
        tk.Label(
            result_shell,
            textvariable=self.spellcheck_corrected_var,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            font=self.fonts["body"],
            wraplength=1040,
            justify="left",
            padx=12,
            pady=10,
        ).pack(fill="x", pady=(6, 10))

        tk.Label(result_shell, text='Error Analysis', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["subtitle"]).pack(
            anchor="w"
        )
        self.spellcheck_suggestions_widget = self._text_panel(result_shell, height=8)
        self.spellcheck_suggestions_widget.pack(fill="both", expand=True, pady=(6, 0))

    def _build_assistant_page(self, parent: tk.Frame) -> None:
        top = self._card(parent)
        top.pack(fill="x", pady=(0, 16))
        tk.Label(top, text='AI Assistant', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["title"]).pack(anchor="w")
        tk.Label(top, textvariable=self.assistant_meta_var, bg=self.colors["surface"], fg=self.colors["muted"], font=self.fonts["subtitle"]).pack(
            anchor="w", pady=(4, 10)
        )
        self.assistant_input_widget = self._text_panel(top, height=5)
        self.assistant_input_widget.pack(fill="x", expand=False)
        ask_actions = tk.Frame(top, bg=self.colors["surface"])
        ask_actions.pack(fill="x", pady=(12, 0))
        self._action_button(ask_actions, 'Ask Assistant', self.ask_assistant, self.colors["primary"]).pack(side="left")
        self._action_button(ask_actions, 'Use Current Word', self.seed_assistant_prompt, self.colors["accent_alt"]).pack(side="left", padx=8)

        bottom = self._card(parent)
        bottom.pack(fill="both", expand=True)
        tk.Label(bottom, text='Assistant Response', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["title"]).pack(anchor="w")
        self.assistant_output_widget = self._text_panel(bottom, height=22)
        self.assistant_output_widget.pack(fill="both", expand=True, pady=(12, 0))

    def _build_benchmark_page(self, parent: tk.Frame) -> None:
        top = self._card(parent)
        top.pack(fill="x", pady=(0, 16))
        tk.Label(top, text='Benchmark And Profiling', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["title"]).pack(
            anchor="w"
        )
        tk.Label(
            top,
            text='The benchmark has been checked against the current database layout. Use this page to rerun lookup and prefix timings.',
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=self.fonts["subtitle"],
            wraplength=780,
            justify="left",
        ).pack(anchor="w", pady=(6, 12))
        actions = tk.Frame(top, bg=self.colors["surface"])
        actions.pack(fill="x")
        self._action_button(actions, 'Run Benchmark', self.run_benchmark, self.colors["primary"]).pack(side="left")
        self._action_button(actions, 'Run Profile', self.run_profile_report, self.colors["accent_alt"]).pack(side="left", padx=8)

        bottom = self._card(parent)
        bottom.pack(fill="both", expand=True)
        tk.Label(bottom, text='Output', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["title"]).pack(anchor="w")
        self.bench_output_widget = self._text_panel(bottom, height=22)
        self.bench_output_widget.pack(fill="both", expand=True, pady=(12, 0))

    def _card(self, parent: tk.Widget) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=self.colors["surface"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=20,
            pady=20,
        )

    def _text_panel(self, parent: tk.Widget, height: int) -> ScrolledText:
        widget = ScrolledText(
            parent,
            wrap="word",
            height=height,
            relief="flat",
            bd=0,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            font=self.fonts["body"],
        )
        widget.configure(padx=12, pady=12)
        return widget

    def _action_button(self, parent: tk.Widget, text: str, command, color: str) -> tk.Button:
        fg = "white"
        return tk.Button(
            parent,
            text=text,
            command=command,
            relief="flat",
            bd=0,
            padx=14,
            pady=10,
            bg=color,
            fg=fg,
            activebackground=color,
            activeforeground=fg,
            font=self.fonts["button"],
            cursor="hand2",
        )

    def _flash_button(self, parent: tk.Widget, text: str, command, color: str) -> tk.Button:
        dark_colors = {self.flash_colors["panel"], self.flash_colors["accent"], self.flash_colors["accent_dark"]}
        fg = "white" if color in dark_colors else self.flash_colors["text"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            bg=color,
            fg=fg,
            activebackground=self.flash_colors["accent"],
            activeforeground="white",
            font=self.fonts["button"],
            cursor="hand2",
        )

    def _bind_flashcard_click_targets(self, widget: tk.Widget) -> None:
        if isinstance(widget, tk.Scrollbar):
            return
        widget.bind("<Button-1>", self._handle_flashcard_click)
        for child in widget.winfo_children():
            self._bind_flashcard_click_targets(child)

    def _handle_flashcard_click(self, event: tk.Event) -> str:
        if not self.flashcard_words or self.flashcard_animating:
            return "break"
        card = self.flashcard_card_frame
        if card is None:
            return "break"
        width = max(card.winfo_width(), 1)
        click_x = event.x_root - card.winfo_rootx()
        left_limit = width * 0.33
        right_limit = width * 0.67
        if click_x <= left_limit:
            self.prev_flashcard()
        elif click_x >= right_limit:
            self.next_flashcard()
        else:
            self.reveal_flashcard()
        return "break"

    def _header_label(self, parent: tk.Widget, text: str) -> tk.Label:
        return tk.Label(parent, text=text, bg=self.colors["header"], fg="white", font=self.fonts["subtitle"])

    def _option_menu(self, parent: tk.Widget, variable: tk.StringVar, values: list[str], command) -> tk.OptionMenu:
        menu = tk.OptionMenu(parent, variable, *values, command=command)
        menu.configure(
            relief="flat",
            bd=0,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            activebackground=self.colors["surface"],
            activeforeground=self.colors["text"],
            highlightthickness=0,
            font=self.fonts["button"],
            padx=8,
            pady=4,
        )
        menu["menu"].configure(bg=self.colors["surface"], fg=self.colors["text"], activebackground=self.colors["hero"])
        return menu

    def _restore_panels(self) -> None:
        self._write_text(self.local_output, self.lookup_meaning_text)
        self._render_hint_panel()
        self._write_text(self.pronounce_output, self.pronounce_text)
        self._write_text(self.summary_output, self.summary_text)
        self._write_text(self.review_output, self.review_text)
        self._render_flashcard()
        self._render_spellcheck_output(self.spellcheck_result_text, [])
        self._write_text(self.spellcheck_suggestions_widget, self.spellcheck_suggestions_text)
        self._write_text(self.assistant_output_widget, self.assistant_output_text)
        self._write_text(self.bench_output_widget, self.bench_output_text)
        self._set_text_widget(self.assistant_input_widget, self.assistant_question_text)
        self._set_text_widget(self.spellcheck_input_widget, self.spellcheck_input_text)
        self._populate_review_listbox()

    def apply_ui_preferences(self, *_args) -> None:
        self._snapshot_inputs()
        self._configure_theme()
        save_json(
            self.store.paths.ui_settings_json,
            {"theme": self.theme_var.get(), "font_size": self.font_size_var.get()},
        )
        self._build_layout()
        self.show_page(self.current_page)

    def _snapshot_inputs(self) -> None:
        self.assistant_question_text = self._get_text_widget(self.assistant_input_widget)
        self.spellcheck_input_text = self._get_text_widget(self.spellcheck_input_widget)

    def show_page(self, page_id: str) -> None:
        self.current_page = page_id
        active_bg = self.colors.get("nav_active", self.colors["primary"])
        inactive_bg = self.colors["header"]
        for current_id, frame in self.pages.items():
            if current_id not in self.nav_buttons:
                continue
            if current_id == page_id:
                frame.lift()
                self.nav_buttons[current_id].configure(
                    bg=active_bg, fg="white", font=self.fonts["nav_item_active"]
                )
            else:
                self.nav_buttons[current_id].configure(
                    bg=inactive_bg, fg=self.colors["text"], font=self.fonts["nav_item"]
                )
        if page_id == "review":
            self._refresh_review_state()
        if page_id == "flashcards":
            self._refresh_flashcards(reset=not self.flashcard_words)

    def init_demo(self) -> None:
        self.store.build_from_mapping(DEMO_ENTRIES)
        self.review_store.load()
        self._load_vietnamese_meanings()
        self._refresh_spell_vocabulary()
        self._render_summary()
        self._refresh_review_state()
        self._refresh_flashcards(reset=True)
        self._update_stats()
        self.status_var.set(f"Initialized demo data in {self.data_dir}")
        messagebox.showinfo("Dictionary App", 'Demo data initialized.')

    def reload_data(self) -> None:
        try:
            self.store.load_if_available()
            self.review_store.load()
            self._load_vietnamese_meanings()
            self._audio_count_cache = None  # refresh audio count on reload
            self._refresh_spell_vocabulary()
            self._render_summary()
            self._refresh_review_state()
            self._refresh_flashcards(reset=True)
            self._update_stats()
            self.status_var.set(f"Reloaded data from {self.data_dir}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('Reload Error', str(exc))

    def _refresh_spell_vocabulary(self) -> None:
        base_words = {
            "a",
            "am",
            "an",
            "and",
            "are",
            "at",
            "be",
            "boy",
            "for",
            "from",
            "girl",
            "he",
            "i",
            "in",
            "is",
            "it",
            "of",
            "on",
            "or",
            "she",
            "that",
            "the",
            "their",
            "there",
            "they",
            "this",
            "to",
            "was",
            "we",
            "were",
            "you",
        }
        dictionary_words = {normalize_word(word) for word in self.store.all_words()}
        self.spell_vocabulary = {word for word in (base_words | dictionary_words) if word}
        self.spell_candidates = sorted(self.spell_vocabulary)

    def load_spellcheck_example(self) -> None:
        sentence = "i was a boy"
        self._set_text_widget(self.spellcheck_input_widget, sentence)
        self.check_sentence_spelling()

    def clear_spellcheck(self) -> None:
        self.spellcheck_meta_var.set('Paste a sentence to auto-fix grammar and analyze.')
        self.spellcheck_corrected_var.set('Corrected sentence will appear here.')
        self.spellcheck_result_text = 'Enter a sentence and click Check Grammar.'
        self.spellcheck_suggestions_text = 'Error analysis will appear here.'
        self._set_text_widget(self.spellcheck_input_widget, "")
        self._render_spellcheck_output(self.spellcheck_result_text, [])
        self._write_text(self.spellcheck_suggestions_widget, self.spellcheck_suggestions_text)

    def check_sentence_spelling(self) -> None:
        sentence = self._get_text_widget(self.spellcheck_input_widget).strip()
        if not sentence:
            messagebox.showwarning('Grammar', 'Enter a sentence first.')
            return
        issues, corrected = self._analyze_sentence_corrections(sentence, self.spell_vocabulary, self.spell_candidates)
        self.spellcheck_result_text = sentence
        self._render_spellcheck_output(sentence, issues)
        self.spellcheck_corrected_var.set(corrected)
        if issues:
            self.spellcheck_meta_var.set(f"Auto-corrected {len(issues)} issue(s).")
            analysis_lines = [
                f"{index}. '{issue['original']}' -> '{issue['suggestion']}' | {issue['reason']}"
                for index, issue in enumerate(issues, start=1)
            ]
            self.spellcheck_suggestions_text = "\n".join(analysis_lines)
            if corrected != sentence:
                self._set_text_widget(self.spellcheck_input_widget, corrected)
            self.status_var.set(f"Auto-corrected {len(issues)} issue(s).")
        else:
            self.spellcheck_meta_var.set('No spelling or grammar issues detected.')
            self.spellcheck_suggestions_text = 'No issues found. Sentence is already correct.'
            self.status_var.set('Grammar check found no issues.')
        self._write_text(self.spellcheck_suggestions_widget, self.spellcheck_suggestions_text)

    def _render_spellcheck_output(self, sentence: str, issues: list[dict[str, object]]) -> None:
        widget = self.spellcheck_output_widget
        if widget is None:
            return
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", sentence)
        widget.tag_remove("error", "1.0", tk.END)
        for issue in issues:
            start = int(issue["start"])
            end = int(issue["end"])
            widget.tag_add("error", f"1.0 + {start} chars", f"1.0 + {end} chars")
        widget.configure(state="disabled")

    @staticmethod
    def _apply_case(original: str, suggestion: str) -> str:
        if not original:
            return suggestion
        if original.isupper():
            return suggestion.upper()
        if original[0].isupper():
            return suggestion.capitalize()
        return suggestion

    @staticmethod
    def _analyze_sentence_corrections(
        sentence: str,
        vocabulary: set[str] | None = None,
        candidates: list[str] | None = None,
    ) -> tuple[list[dict[str, object]], str]:
        token_matches = list(re.finditer(r"[A-Za-z']+", sentence))
        tokens = [(match.group(0), match.start(), match.end()) for match in token_matches]
        issues: list[dict[str, object]] = []
        seen_spans: set[tuple[int, int]] = set()

        vocab = vocabulary or set()
        lookups = candidates or sorted(vocab)

        def add_issue(start: int, end: int, original: str, suggestion: str, reason: str) -> None:
            if not suggestion or suggestion == original:
                return
            span = (start, end)
            if span in seen_spans:
                return
            seen_spans.add(span)
            issues.append(
                {
                    "start": start,
                    "end": end,
                    "original": original,
                    "suggestion": suggestion,
                    "reason": reason,
                }
            )

        for index, (token, start, end) in enumerate(tokens):
            lower = token.lower()
            previous = tokens[index - 1][0].lower() if index > 0 else ""
            next_word = tokens[index + 1][0].lower() if index + 1 < len(tokens) else ""

            if lower == "i" and token != "I":
                add_issue(start, end, token, "I", "Pronoun 'I' should be uppercase.")
            if previous == "i" and lower in {"is", "are", "was", "were"}:
                add_issue(start, end, token, DictionaryAppGUI._apply_case(token, "am"), "Use 'am' after 'I'.")
                continue
            if previous in {"he", "she", "it"} and lower in {"are", "were"}:
                add_issue(start, end, token, DictionaryAppGUI._apply_case(token, "is"), "Use 'is' with he/she/it.")
                continue
            if previous in {"you", "we", "they"} and lower in {"is", "was"}:
                add_issue(start, end, token, DictionaryAppGUI._apply_case(token, "are"), "Use 'are' with you/we/they.")
                continue
            if lower == "a" and next_word and next_word[0] in "aeiou":
                add_issue(start, end, token, DictionaryAppGUI._apply_case(token, "an"), "Use 'an' before vowel sounds.")
            if lower == "an" and next_word and next_word[0] not in "aeiou":
                add_issue(start, end, token, DictionaryAppGUI._apply_case(token, "a"), "Use 'a' before consonant sounds.")

            if not vocab or len(lower) <= 2:
                continue
            if lower in vocab:
                continue
            if token[0].isupper():
                continue
            close_matches = difflib.get_close_matches(lower, lookups, n=1, cutoff=0.84)
            if close_matches:
                suggestion = DictionaryAppGUI._apply_case(token, close_matches[0])
                add_issue(start, end, token, suggestion, 'Possible spelling mistake.')

        issues.sort(key=lambda issue: int(issue["start"]))
        corrected_parts: list[str] = []
        cursor = 0
        for issue in issues:
            start = int(issue["start"])
            end = int(issue["end"])
            suggestion = str(issue["suggestion"])
            if start < cursor:
                continue
            corrected_parts.append(sentence[cursor:start])
            corrected_parts.append(suggestion)
            cursor = end
        corrected_parts.append(sentence[cursor:])
        corrected_sentence = "".join(corrected_parts)
        return issues, corrected_sentence

    def lookup_word(self) -> None:
        word = self.lookup_word_var.get().strip()
        if not word:
            messagebox.showwarning('Lookup', 'Enter a word first.')
            return
        try:
            meaning = self.store.lookup(word) if self.store.hash_index else None
            source = "database local"
            if meaning is None:
                # Show a loading indicator while fetching online
                self.status_var.set(f"Looking up '{word}' online…")
                self.root.update_idletasks()
                self._lookup_online_async(word)
                return

            self._finalize_lookup(word, meaning, source)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('Lookup Error', str(exc))

    def _lookup_online_async(self, word: str) -> None:
        """Fetch definition from online API in a background thread."""
        def _fetch():
            try:
                resolved = auto_define_word(self.store, self.online_client, word)
                self.root.after(0, lambda: self._on_online_lookup_done(word, resolved))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror('Lookup Error', str(exc)))
        threading.Thread(target=_fetch, daemon=True).start()

    def _on_online_lookup_done(self, word: str, resolved) -> None:
        """Handle online lookup result on the main thread."""
        if resolved.usable:
            meaning = self.store.lookup(word) or resolved.meaning
            source = 'saved to local database from online lookup'
            self._sync_pronunciation_cache(word, resolved.entry.phonetic)
            self._audio_count_cache = None  # new entry may have audio
            self._finalize_lookup(word, meaning, source)
        else:
            self.current_lookup_word = word
            self.current_lookup_meaning = ""
            self.result_word_var.set(word)
            self.result_meta_var.set('No local entry was saved for this word.')
            self.lookup_meaning_text = 'No definition is available in the local database.'
            self.hint_meta_var.set('AI usage hint')
            self.hint_text = 'No usage hint is available because the word could not be saved.'
            self.hint_chat_history = []
            self.hint_question_var.set("")
            self._render_pronunciation(word, "")
            self._push_search_panels()
            self.status_var.set(f"No local or online meaning found for '{word}'.")

    def _finalize_lookup(self, word: str, meaning: str, source: str) -> None:
        """Common path to display lookup results (local or online)."""
        normalized = normalize_word(word)
        self.current_lookup_word = normalized or word.strip()
        self.current_lookup_meaning = meaning or ""
        self.result_word_var.set(self.current_lookup_word)
        self.result_meta_var.set(f"Showing {source}.")
        self.lookup_meaning_text = self._format_meaning_for_display(self.current_lookup_meaning)
        self._load_usage_hint(self.current_lookup_word, self.current_lookup_meaning)
        self._render_pronunciation(self.current_lookup_word, self.current_lookup_meaning)
        self._push_search_panels()
        if source == "database local":
            self.status_var.set(f"Read '{self.current_lookup_word}' from the local database.")
        else:
            self.status_var.set(f"Fetched '{self.current_lookup_word}' once and saved it to the local database.")
        # Defer heavy refreshes to avoid blocking the UI
        self.root.after_idle(self._render_summary)
        self.root.after_idle(self._update_stats)
        self.root.after_idle(lambda: self._refresh_flashcards(reset=False))

    def _load_usage_hint(self, word: str, meaning: str) -> None:
        try:
            hint_payload = self.ai_client.usage_hint(word, meaning) if self.ai_client.enabled else self._fallback_usage_hint(word, meaning)
        except Exception:
            hint_payload = self._fallback_usage_hint(word, meaning)
        self.hint_meta_var.set('AI hint + follow-up chat')
        self.hint_text = self._format_hint_for_display(hint_payload)
        self.hint_chat_history = []
        self.hint_question_var.set("")

    def ask_hint_question(self, question: str | None = None) -> None:
        word = self.current_lookup_word or self.lookup_word_var.get().strip()
        if not word:
            messagebox.showwarning('Hint', 'Search a word first.')
            return
        asked = (question or self.hint_question_var.get()).strip()
        if not asked:
            messagebox.showwarning('Hint', 'Enter a question first.')
            return

        meaning = self.current_lookup_meaning or (self.store.lookup(word) or "")
        if self.ai_client.enabled:
            history_context = self._hint_history_context()
            prompt = asked if not history_context else f"{history_context}\n\nFollow-up question: {asked}"
            try:
                answer = self.ai_client.assistant_reply(prompt, word=word, meaning=meaning)
            except Exception:
                answer = self._fallback_hint_answer(word, meaning, asked)
        else:
            answer = self._fallback_hint_answer(word, meaning, asked)

        self.hint_chat_history.append((asked, answer.strip()))
        self.hint_chat_history = self.hint_chat_history[-8:]
        self.hint_question_var.set("")
        self.hint_meta_var.set(f"AI hint chat for '{word}'")
        self._render_hint_panel()
        self.status_var.set('Hint response updated.')

    def _hint_history_context(self) -> str:
        if not self.hint_chat_history:
            return ""
        lines = ['Conversation context:']
        for asked, answered in self.hint_chat_history[-3:]:
            lines.append(f"User: {asked}")
            lines.append(f"Assistant: {answered}")
        return "\n".join(lines)

    def _fallback_hint_answer(self, word: str, meaning: str, question: str) -> str:
        base = self._fallback_usage_hint(word, meaning)
        lowered = question.lower()
        if "example" in lowered:
            return f"Example with '{word}': {base.get('example', '') or f'I used {word} in a sentence.'}"
        if "mistake" in lowered or "avoid" in lowered:
            return f"Common mistake: use '{word}' in the right context and tone.\nTip: {base.get('tone', '')}"
        if "compare" in lowered or "similar" in lowered:
            return f"Compare by context: {base.get('when_to_use', '')}\nTry a few synonyms and compare tone."
        return "\n".join(
            [
                f"When to use: {base.get('when_to_use', '')}",
                f"Tone: {base.get('tone', '')}",
                f"Situations: {base.get('common_situations', '')}",
                f"Example: {base.get('example', '')}",
            ]
        ).strip()

    def _render_hint_panel(self) -> None:
        sections = [self.hint_text.strip()]
        if self.hint_chat_history:
            chat_lines = ['Follow-up Q&A:']
            for index, (asked, answered) in enumerate(self.hint_chat_history, start=1):
                chat_lines.append(f"Q{index}: {asked}")
                chat_lines.append(f"A{index}: {answered}")
            sections.append("\n".join(chat_lines))
        payload = "\n\n".join(section for section in sections if section)
        self._write_text(self.hint_output, payload or 'Hint output is empty.')

    def _fallback_usage_hint(self, word: str, meaning: str) -> dict[str, str]:
        hints = {
            "hi": {
                "when_to_use": "Use it in daily greetings, informal conversations, or when asking how someone is doing.",
                "tone": "Friendly and casual.",
                "common_situations": "meeting friends, texting, checking on someone",
                "example": "Hi, how are you feeling today?",
            },
            "hello": {
                "when_to_use": "Use it when greeting someone in most common situations.",
                "tone": "Neutral and polite.",
                "common_situations": "phone calls, meeting someone, starting a conversation",
                "example": "Hello, nice to meet you.",
            },
        }
        if word in hints:
            return hints[word]
        brief = self._format_meaning_for_display(meaning).splitlines()[0] if meaning else "this word"
        return {
            "when_to_use": f"Use it when you want to talk about {brief.lower()}.",
            "tone": "Check the sentence context to decide if it sounds formal or casual.",
            "common_situations": "general English communication and study examples",
            "example": f"Try making a simple sentence with '{word}'.",
        }

    def _format_hint_for_display(self, payload: dict[str, object]) -> str:
        def clean(value: object) -> str:
            return str(value or "").strip()

        lines = [
            f"Khi dùng: {clean(payload.get('when_to_use', ''))}",
            f"Sắc thái: {clean(payload.get('tone', ''))}",
            f"Tình huống thường gặp: {clean(payload.get('common_situations', ''))}",
            f"Ví dụ: {clean(payload.get('example', ''))}",
        ]
        return "\n\n".join(line for line in lines if not line.endswith(": "))

    def _render_pronunciation(self, word: str, meaning: str) -> None:
        ipa = self.phonetics.get_ipa(word) or self._local_ipa_from_meaning(meaning)
        if ipa:
            self._sync_pronunciation_cache(word, ipa)
        audio_path = self.phonetics.audio_path(word)
        self.pronounce_meta_var.set(f"Provider: {self.phonetics.provider_name()}")
        if ipa:
            self.pronounce_text = "\n".join(
                [
                    f"IPA: {ipa}",
                    f"Audio cache: {'Available' if audio_path.exists() else 'Not saved yet'}",
                    f"Audio file: {audio_path.name}",
                ]
            )
        else:
            self.pronounce_text = 'No IPA has been saved for this word in the local database.'
        self._write_text(self.pronounce_output, self.pronounce_text)

    def generate_pronunciation_audio(self) -> None:
        word = self.lookup_word_var.get().strip()
        if not word:
            messagebox.showwarning('Pronounce', 'Enter a word first.')
            return
        try:
            audio_path = self.phonetics.generate_audio(word)
            self.phonetics.play_audio(audio_path)
            meaning = self.store.lookup(word) or ""
            self._render_pronunciation(word, meaning)
            self._audio_count_cache = None  # new audio file created
            self._render_summary()
            self.status_var.set(f"Generated and played audio for '{normalize_word(word) or word}'.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('Pronounce Error', str(exc))

    def play_pronunciation_audio(self) -> None:
        word = self.lookup_word_var.get().strip()
        if not word:
            messagebox.showwarning('Pronounce', 'Enter a word first.')
            return
        audio_path = self.phonetics.audio_path(word)
        if not audio_path.exists():
            messagebox.showwarning('Pronounce', 'No cached audio file exists for this word yet.')
            return
        try:
            self.phonetics.play_audio(audio_path)
            self.status_var.set(f"Playing cached audio for '{normalize_word(word) or word}'.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('Pronounce Error', str(exc))

    def stop_pronunciation_audio(self) -> None:
        self.phonetics.stop_audio()
        self.status_var.set('Stopped audio playback.')

    def schedule_current_word(self) -> None:
        if not self.current_lookup_word:
            messagebox.showwarning('Review', 'Search a word first.')
            return
        added = self.review_store.schedule_tomorrow([self.current_lookup_word])
        self._refresh_review_state()
        self._render_summary()
        self.status_var.set(f"Scheduled '{self.current_lookup_word}' for review. New item count: {added}")

    def _refresh_review_state(self) -> None:
        due_items = self.review_store.due_items()
        self.review_meta_var.set(f"{len(due_items)} due today")
        self.review_word_var.set(due_items[0].word if due_items else 'No words due today')
        self._populate_review_listbox()
        self._render_review_from_word(due_items[0].word if due_items else "")
        self._render_summary()
        self._update_stats()

    def _populate_review_listbox(self) -> None:
        if self.review_listbox is None:
            return
        self.review_listbox.delete(0, tk.END)
        for item in self.review_store.due_items():
            self.review_listbox.insert(tk.END, item.word)

    def _select_review_item(self, _event) -> None:
        if self.review_listbox is None:
            return
        selection = self.review_listbox.curselection()
        if not selection:
            return
        word = self.review_listbox.get(selection[0])
        self._render_review_from_word(word)

    def _render_review_from_word(self, word: str) -> None:
        if not word:
            self.review_word_var.set('No words due today')
            self.review_text = 'Use Search to build a review queue.'
            self._write_text(self.review_output, self.review_text)
            return
        item = self.review_store.items.get(word)
        if item is None:
            self.review_word_var.set(word)
            self.review_text = 'The selected review item no longer exists.'
            self._write_text(self.review_output, self.review_text)
            return

        self.review_word_var.set(self._uppercase_first_character(word))

        # Build card content
        sections = []

        # English meaning
        meaning = self.store.lookup(word) or ''
        if meaning:
            formatted = self._format_meaning_for_display(meaning).strip()
            sections.append(formatted)
        else:
            sections.append('No local meaning stored.')

        # Vietnamese meaning
        vn_meaning = self._get_vietnamese_meaning_from_database(normalize_word(word))
        if vn_meaning:
            sections.append(f"🇻🇳  {vn_meaning}")

        # Usage hint
        cached_hint = self.ai_client.cache.get(f"usage|{word}|en")
        hint = cached_hint if isinstance(cached_hint, dict) else None
        if hint:
            hint_text = self._format_hint_for_display(hint)
            if hint_text:
                sections.append(f"💡 When to use:\n{hint_text}")

        # Schedule
        if item:
            schedule = f"📅 Next: {item.next_review_date} | Interval: {item.interval_days}d | ✔ {item.right_count} | ✘ {item.wrong_count} | Last: {item.last_result}"
            sections.append(schedule)

        self.review_text = "\n\n".join(sections)
        self._write_text(self.review_output, self.review_text)

    def review_current(self, remembered: bool) -> None:
        word = self.review_word_var.get().strip()
        if not word or word == 'No words due today':
            return
        updated = self.review_store.record_result(word, remembered=remembered)
        self.status_var.set(f"{updated.word}: {updated.last_result}, next review {updated.next_review_date}")
        self._refresh_review_state()

    def _change_flashcard_mode(self, *_args) -> None:
        self._refresh_flashcards(reset=True)

    def _refresh_flashcards(self, reset: bool) -> None:
        self._cancel_flashcard_transition()
        mode = self.flashcard_mode_var.get()
        custom_words = self.flashcard_store.card_words()
        if mode == 'Due Today':
            due_words = [item.word for item in self.review_store.due_items()]
            self.flashcard_words = self._unique_words(due_words or (self.store.all_words() + custom_words))
        elif mode == 'Custom Cards':
            self.flashcard_words = self._unique_words(custom_words)
        else:
            self.flashcard_words = self._unique_words(self.store.all_words() + custom_words)
        if reset:
            self.flashcard_index = 0
            self.flashcard_answer_shown = False
        if self.flashcard_index >= len(self.flashcard_words):
            self.flashcard_index = 0
        self._render_flashcard()

    def _unique_words(self, words: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for word in words:
            key = normalize_word(word)
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(word)
        return unique

    def shuffle_flashcards(self) -> None:
        self._cancel_flashcard_transition()
        random.shuffle(self.flashcard_words)
        self.flashcard_index = 0
        self.flashcard_answer_shown = False
        self._render_flashcard()

    def _cancel_flashcard_transition(self) -> None:
        if self.flashcard_transition_job:
            try:
                self.root.after_cancel(self.flashcard_transition_job)
            except Exception:  # noqa: BLE001
                pass
            self.flashcard_transition_job = None
        self.flashcard_animating = False
        if self.flashcard_content_frame is not None:
            self.flashcard_content_frame.place_configure(x=0, y=0, relwidth=1, relheight=1)

    def _animate_flashcard_transition(self, direction: int) -> None:
        card = self.flashcard_card_frame
        content = self.flashcard_content_frame
        if card is None or content is None:
            self._render_flashcard()
            return
        card.update_idletasks()
        width = card.winfo_width()
        if width < 10:
            self._render_flashcard()
            return
        self._cancel_flashcard_transition()
        self.flashcard_animating = True
        steps = 8
        interval_ms = 16
        exit_x = -width if direction > 0 else width
        enter_start_x = width if direction > 0 else -width

        def slide_out(step: int) -> None:
            ratio = step / steps
            x = int(exit_x * ratio)
            content.place_configure(x=x, y=0, relwidth=1, relheight=1)
            if step < steps:
                self.flashcard_transition_job = self.root.after(interval_ms, slide_out, step + 1)
                return
            self._render_flashcard()
            content.place_configure(x=enter_start_x, y=0, relwidth=1, relheight=1)
            slide_in(0)

        def slide_in(step: int) -> None:
            ratio = step / steps
            x = int(enter_start_x * (1 - ratio))
            content.place_configure(x=x, y=0, relwidth=1, relheight=1)
            if step < steps:
                self.flashcard_transition_job = self.root.after(interval_ms, slide_in, step + 1)
                return
            content.place_configure(x=0, y=0, relwidth=1, relheight=1)
            self.flashcard_transition_job = None
            self.flashcard_animating = False

        slide_out(0)

    def _render_flashcard(self) -> None:
        if not self.flashcard_words:
            self.flashcard_word_var.set('No cards')
            self.flashcard_meta_var.set('Create cards or load a deck to practice.')
            self.flashcard_progress_var.set("0 / 0")
            self.flashcard_card_hint_var.set("")
            self._write_flashcard_text('The flashcard deck is empty.')
            return
        word = self.flashcard_words[self.flashcard_index]
        self.flashcard_word_var.set(self._uppercase_first_character(word))
        self.flashcard_meta_var.set(
            f"{self.flashcard_mode_var.get()} deck | {len(self.flashcard_words)} cards | custom {len(self.flashcard_store.cards)}"
        )
        self.flashcard_progress_var.set(f"{self.flashcard_index + 1} / {len(self.flashcard_words)}")
        self.flashcard_card_hint_var.set("")
        if self.flashcard_card_frame is not None:
            self.flashcard_card_frame.configure(bg=self.flash_colors["panel_alt"] if self.flashcard_answer_shown else self.flash_colors["card"])
        if self.flashcard_content_frame is not None:
            self.flashcard_content_frame.configure(
                bg=self.flash_colors["panel_alt"] if self.flashcard_answer_shown else self.flash_colors["card"]
            )
        self._write_flashcard_text(self._current_flashcard_text())

    def _current_flashcard_text(self) -> str:
        if not self.flashcard_words:
            return 'The flashcard deck is empty.'
        if not self.flashcard_answer_shown:
            return ""
        word = self.flashcard_words[self.flashcard_index]
        return self._flashcard_answer_for_word(word)

    def _basic_flashcard_meaning(self, meaning: str) -> str:
        cleaned = self._format_meaning_for_display(meaning).strip()
        if not cleaned:
            return 'No local meaning stored.'
        first_block = cleaned.split("\n\n", 1)[0].strip()
        first_line = first_block.splitlines()[0].strip()
        return first_line or cleaned

    @staticmethod
    def _uppercase_first_character(value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return ""
        return cleaned[0].upper() + cleaned[1:]

    def _flashcard_answer_for_word(self, word: str) -> str:
        custom_card = self.flashcard_store.get(word)
        if custom_card is not None:
            payload = custom_card.back.strip()
            return payload if payload else 'No custom meaning yet.'
        meaning = self.store.lookup(word) or 'No local meaning stored.'
        return self._basic_flashcard_meaning(meaning)

    def _build_flashcard_match_pairs(self, limit: int = 8) -> list[tuple[str, str, str]]:
        if not self.flashcard_words:
            self._refresh_flashcards(reset=True)
        candidates = list(self.flashcard_words)
        random.shuffle(candidates)
        pairs: list[tuple[str, str, str]] = []
        used_meanings: set[str] = set()
        for word in candidates:
            key = normalize_word(word)
            if not key:
                continue
            meaning = " ".join(self._flashcard_answer_for_word(word).split()).strip()
            if not meaning:
                continue
            if len(meaning) > 100:
                meaning = f"{meaning[:97].rstrip()}..."
            meaning_key = meaning.lower()
            if meaning_key in used_meanings:
                continue
            used_meanings.add(meaning_key)
            pairs.append((key, self._uppercase_first_character(word), meaning))
            if len(pairs) >= limit:
                break
        return pairs

    def _open_flashcard_match_game(self, pairs: list[tuple[str, str, str]]) -> None:
        game = tk.Toplevel(self.root)
        game.title('Flashcard Match Game')
        game.geometry("980x680")
        game.minsize(860, 600)
        game.configure(bg=self.flash_colors["bg"])
        game.transient(self.root)
        game.grab_set()

        shell = tk.Frame(game, bg=self.flash_colors["bg"], padx=14, pady=14)
        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg=self.flash_colors["bg"])
        header.pack(fill="x")
        tk.Label(
            header,
            text='🎮 Match Game',
            bg=self.flash_colors["bg"],
            fg=self.flash_colors["text"],
            font=self.fonts["flash_title"],
        ).pack(side="left")

        stats_var = tk.StringVar(value=f"Correct 0/{len(pairs)} | Time 0.0s")
        stats_label = tk.Label(
            header,
            textvariable=stats_var,
            bg=self.flash_colors["bg"],
            fg=self.flash_colors["muted"],
            font=self.fonts["subtitle"],
        )
        stats_label.pack(side="left", padx=(12, 0))

        controls = tk.Frame(header, bg=self.flash_colors["bg"])
        controls.pack(side="right")

        instruction_label = tk.Label(
            shell,
            text='Pick 1 word and 1 meaning. Correct matches stay locked.',
            bg=self.flash_colors["bg"],
            fg=self.flash_colors["muted"],
            font=self.fonts["subtitle"],
        )
        instruction_label.pack(anchor="w", pady=(6, 6))

        progress_shell = tk.Frame(shell, bg=self.flash_colors["bg"])
        progress_shell.pack(fill="x", pady=(0, 8))
        progress_track = tk.Frame(
            progress_shell,
            bg=self.flash_colors["panel_alt"],
            height=8,
            highlightthickness=1,
            highlightbackground=self.flash_colors["line"],
        )
        progress_track.pack(fill="x")
        progress_fill = tk.Frame(progress_track, bg="#2fbf71", height=8)
        progress_fill.place(x=0, y=0, width=0, relheight=1)

        celebration_var = tk.StringVar(value="")
        celebration_label = tk.Label(
            shell,
            textvariable=celebration_var,
            bg=self.flash_colors["bg"],
            fg="#7de3aa",
            font=self.fonts["title"],
        )
        celebration_label.pack(anchor="w", pady=(0, 4))

        finished = {"value": False}
        timer_job = {"id": None}
        start_time = time.perf_counter()
        matched_count = {"value": 0}
        selected = {"word": None, "meaning": None}
        locked = {"value": False}
        celebration_job = {"id": None}

        word_buttons: dict[str, tk.Button] = {}
        meaning_buttons: dict[str, tk.Button] = {}
        match_green = "#2fbf71"
        mismatch_red = "#d9534f"
        hover_color = "#3f5aa3"

        def elapsed_seconds() -> float:
            return max(0.0, time.perf_counter() - start_time)

        def update_progress_bar() -> None:
            total = len(pairs)
            ratio = (matched_count["value"] / total) if total else 0.0
            track_width = max(progress_track.winfo_width(), 1)
            progress_fill.place_configure(width=max(0, int(track_width * ratio)))

        def update_stats() -> None:
            stats_var.set(f"Correct {matched_count['value']}/{len(pairs)} | Time {elapsed_seconds():.1f}s")
            update_progress_bar()

        def cancel_celebration() -> None:
            job = celebration_job["id"]
            if job is not None:
                try:
                    game.after_cancel(job)
                except Exception:  # noqa: BLE001
                    pass
                celebration_job["id"] = None

        def cancel_timer() -> None:
            job = timer_job["id"]
            if job is not None:
                try:
                    game.after_cancel(job)
                except Exception:  # noqa: BLE001
                    pass
                timer_job["id"] = None

        def close_game() -> None:
            finished["value"] = True
            cancel_timer()
            cancel_celebration()
            game.destroy()

        def style_default(button: tk.Button) -> None:
            button.configure(bg=self.flash_colors["panel_alt"], fg=self.flash_colors["text"], relief="raised")

        def style_selected(button: tk.Button) -> None:
            button.configure(bg=self.flash_colors["accent"], fg="white", relief="sunken")

        def style_matched(button: tk.Button) -> None:
            button.configure(bg=match_green, fg="white", relief="flat", state="disabled")

        def style_wrong(button: tk.Button) -> None:
            button.configure(bg=mismatch_red, fg="white", relief="sunken")

        def style_hover(button: tk.Button) -> None:
            button.configure(bg=hover_color, fg="white", relief="raised")

        def clear_selection() -> None:
            word_key = selected["word"]
            meaning_key = selected["meaning"]
            if word_key and word_key in word_buttons:
                style_default(word_buttons[word_key])
            if meaning_key and meaning_key in meaning_buttons:
                style_default(meaning_buttons[meaning_key])
            selected["word"] = None
            selected["meaning"] = None

        def finish_game() -> None:
            if finished["value"]:
                return
            finished["value"] = True
            cancel_timer()
            update_stats()
            duration = elapsed_seconds()
            celebration_var.set('Great job! You matched all pairs.')
            stats_label.configure(fg="#7de3aa")
            instruction_label.configure(fg="#cbd4f2")
            self.status_var.set(f"Completed matching in {duration:.1f}s ({len(pairs)} pairs).")
            messagebox.showinfo('Congratulations', f"You matched {len(pairs)} pairs in {duration:.1f} seconds.")

            pulse_colors = ["#7de3aa", "#f8f9ff"]

            def pulse(index: int) -> None:
                if not game.winfo_exists():
                    return
                celebration_label.configure(fg=pulse_colors[index % len(pulse_colors)])
                celebration_job["id"] = game.after(250, pulse, index + 1)

            pulse(0)

        def evaluate_pair() -> None:
            word_key = selected["word"]
            meaning_key = selected["meaning"]
            if word_key is None or meaning_key is None:
                return
            if word_key == meaning_key:
                style_matched(word_buttons[word_key])
                style_matched(meaning_buttons[meaning_key])
                matched_count["value"] += 1
                selected["word"] = None
                selected["meaning"] = None
                update_stats()
                if matched_count["value"] == len(pairs):
                    finish_game()
                return

            locked["value"] = True
            style_wrong(word_buttons[word_key])
            style_wrong(meaning_buttons[meaning_key])

            def reset_wrong_pair() -> None:
                clear_selection()
                locked["value"] = False

            game.after(260, reset_wrong_pair)

        def select_item(side: str, pair_key: str) -> None:
            if finished["value"] or locked["value"]:
                return
            bucket = word_buttons if side == "word" else meaning_buttons
            current = selected[side]
            if current == pair_key:
                if current in bucket:
                    style_default(bucket[current])
                selected[side] = None
                return
            if current and current in bucket:
                style_default(bucket[current])
            selected[side] = pair_key
            style_selected(bucket[pair_key])
            evaluate_pair()

        def on_item_enter(side: str, pair_key: str, button: tk.Button) -> None:
            if finished["value"] or locked["value"] or str(button.cget("state")) != "normal":
                return
            if selected[side] == pair_key:
                return
            style_hover(button)

        def on_item_leave(side: str, pair_key: str, button: tk.Button) -> None:
            if str(button.cget("state")) != "normal":
                return
            if selected[side] == pair_key:
                style_selected(button)
                return
            style_default(button)

        def tick() -> None:
            if finished["value"] or not game.winfo_exists():
                return
            update_stats()
            timer_job["id"] = game.after(100, tick)

        def start_new_round() -> None:
            close_game()
            self._match_flashcards()

        self._flash_button(controls, 'New Round', start_new_round, self.flash_colors["panel_alt"]).pack(side="left", padx=(0, 6))
        self._flash_button(controls, 'Close', close_game, self.flash_colors["panel"]).pack(side="left")

        board = tk.Frame(
            shell,
            bg=self.flash_colors["bg"],
            highlightthickness=1,
            highlightbackground=self.flash_colors["line"],
            padx=12,
            pady=12,
        )
        board.pack(fill="both", expand=True, pady=(12, 0))

        def sync_progress(_event=None) -> None:
            update_progress_bar()

        progress_track.bind("<Configure>", sync_progress)

        left_column = tk.Frame(board, bg=self.flash_colors["bg"])
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right_column = tk.Frame(board, bg=self.flash_colors["bg"])
        right_column.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(left_column, text='Word', bg=self.flash_colors["bg"], fg=self.flash_colors["muted"], font=self.fonts["subtitle"]).pack(anchor="w")
        tk.Label(right_column, text='Meaning', bg=self.flash_colors["bg"], fg=self.flash_colors["muted"], font=self.fonts["subtitle"]).pack(anchor="w")

        word_items = list(pairs)
        meaning_items = list(pairs)
        random.shuffle(word_items)
        random.shuffle(meaning_items)

        for pair_key, word_label, _meaning in word_items:
            button = tk.Button(
                left_column,
                text=word_label,
                relief="raised",
                bd=1,
                padx=12,
                pady=10,
                anchor="w",
                justify="left",
                wraplength=360,
                bg=self.flash_colors["panel_alt"],
                fg=self.flash_colors["text"],
                activebackground=self.flash_colors["accent"],
                activeforeground="white",
                font=self.fonts["body"],
                cursor="hand2",
                command=lambda key=pair_key: select_item("word", key),
            )
            button.pack(fill="x", pady=(6, 0))
            button.bind("<Enter>", lambda _event, key=pair_key, widget=button: on_item_enter("word", key, widget))
            button.bind("<Leave>", lambda _event, key=pair_key, widget=button: on_item_leave("word", key, widget))
            word_buttons[pair_key] = button

        for pair_key, _word_label, meaning_label in meaning_items:
            button = tk.Button(
                right_column,
                text=meaning_label,
                relief="raised",
                bd=1,
                padx=12,
                pady=10,
                anchor="w",
                justify="left",
                wraplength=380,
                bg=self.flash_colors["panel_alt"],
                fg=self.flash_colors["text"],
                activebackground=self.flash_colors["accent"],
                activeforeground="white",
                font=self.fonts["body"],
                cursor="hand2",
                command=lambda key=pair_key: select_item("meaning", key),
            )
            button.pack(fill="x", pady=(6, 0))
            button.bind("<Enter>", lambda _event, key=pair_key, widget=button: on_item_enter("meaning", key, widget))
            button.bind("<Leave>", lambda _event, key=pair_key, widget=button: on_item_leave("meaning", key, widget))
            meaning_buttons[pair_key] = button

        update_progress_bar()
        game.protocol("WM_DELETE_WINDOW", close_game)
        tick()

    def reveal_flashcard(self) -> None:
        if not self.flashcard_words:
            return
        if self.flashcard_answer_shown:
            return
        self.flashcard_answer_shown = True
        self._render_flashcard()

    def toggle_flashcard_face(self) -> None:
        if not self.flashcard_words:
            return
        self.reveal_flashcard()

    def prev_flashcard(self) -> None:
        if not self.flashcard_words or self.flashcard_animating:
            return
        self.flashcard_index = (self.flashcard_index - 1) % len(self.flashcard_words)
        self.flashcard_answer_shown = False
        self._animate_flashcard_transition(direction=-1)

    def next_flashcard(self) -> None:
        if not self.flashcard_words or self.flashcard_animating:
            return
        self.flashcard_index = (self.flashcard_index + 1) % len(self.flashcard_words)
        self.flashcard_answer_shown = False
        self._animate_flashcard_transition(direction=1)

    def mark_flashcard(self, remembered: bool) -> None:
        if not self.flashcard_words:
            return
        word = self.flashcard_words[self.flashcard_index]
        self.review_store.record_result(word, remembered=remembered)
        self.status_var.set(f"Updated flashcard result for '{word}'.")
        self._refresh_review_state()
        self.next_flashcard()

    def play_flashcard_audio(self) -> None:
        if not self.flashcard_words:
            return
        word = self.flashcard_words[self.flashcard_index]
        try:
            if not self.phonetics.has_audio(word):
                self.phonetics.generate_audio(word)
            self.phonetics.play_audio(self.phonetics.audio_path(word))
            self.status_var.set(f"Playing flashcard audio for '{word}'.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('Flashcards', str(exc))

    def _blast_flashcards(self) -> None:
        self.flashcard_mode_var.set('All Words')
        self._refresh_flashcards(reset=True)
        self.shuffle_flashcards()

    def _match_flashcards(self) -> None:
        pairs = self._build_flashcard_match_pairs(limit=8)
        if len(pairs) < 2:
            messagebox.showwarning('Match Game', 'Need at least 2 cards with meanings to start.')
            return
        self._open_flashcard_match_game(pairs)

    def _quiz_flashcards(self) -> None:
        pairs = self._build_flashcard_match_pairs(limit=30)
        if len(pairs) < 4:
            messagebox.showwarning('Quiz Game', 'Need at least 4 cards with meanings to start.')
            return
        self._open_flashcard_quiz_game(pairs)

    def _open_flashcard_quiz_game(self, pairs: list[tuple[str, str, str]]) -> None:
        game = tk.Toplevel(self.root)
        game.title('Flashcard Quiz Game')
        game.geometry("920x700")
        game.minsize(800, 620)
        game.configure(bg=self.flash_colors["bg"])
        game.transient(self.root)
        game.grab_set()

        shell = tk.Frame(game, bg=self.flash_colors["bg"], padx=18, pady=16)
        shell.pack(fill="both", expand=True)

        top = tk.Frame(shell, bg=self.flash_colors["bg"])
        top.pack(fill="x")
        tk.Label(
            top,
            text='❓ Vocabulary Quiz',
            bg=self.flash_colors["bg"],
            fg=self.flash_colors["text"],
            font=self.fonts["flash_title"],
        ).pack(side="left")

        quiz_stats_var = tk.StringVar(value="")
        tk.Label(
            top,
            textvariable=quiz_stats_var,
            bg=self.flash_colors["bg"],
            fg=self.flash_colors["muted"],
            font=self.fonts["subtitle"],
        ).pack(side="left", padx=(12, 0))

        question_card = tk.Frame(
            shell,
            bg=self.flash_colors["card"],
            highlightthickness=1,
            highlightbackground=self.flash_colors["line"],
            padx=18,
            pady=16,
        )
        question_card.pack(fill="x", pady=(14, 10))

        tk.Label(
            question_card,
            text='Choose the correct meaning of the word',
            bg=self.flash_colors["card"],
            fg=self.flash_colors["muted"],
            font=self.fonts["subtitle"],
        ).pack(anchor="w")

        word_var = tk.StringVar(value="")
        tk.Label(
            question_card,
            textvariable=word_var,
            bg=self.flash_colors["card"],
            fg=self.flash_colors["text"],
            font=self.fonts["flash_word"],
            wraplength=760,
            justify="center",
        ).pack(fill="x", pady=(8, 0))

        feedback_var = tk.StringVar(value="")
        tk.Label(
            question_card,
            textvariable=feedback_var,
            bg=self.flash_colors["card"],
            fg=self.flash_colors["muted"],
            font=self.fonts["subtitle"],
        ).pack(anchor="w", pady=(8, 0))

        options_wrap = tk.Frame(shell, bg=self.flash_colors["bg"])
        options_wrap.pack(fill="both", expand=True)

        option_buttons: list[tk.Button] = []

        question_bank = list(pairs)
        random.shuffle(question_bank)
        total_questions = min(12, len(question_bank))
        question_bank = question_bank[:total_questions]
        all_meanings = [meaning for _, _, meaning in pairs]

        index = {"value": 0}
        score = {"value": 0}
        answered = {"value": False}
        current_answer = {"value": ""}
        start_time = time.perf_counter()
        match_green = "#2fbf71"
        mismatch_red = "#d9534f"
        auto_job = {"id": None}
        timer_job = {"id": None}
        time_limit = 120  # 2 minutes

        timer_var = tk.StringVar(value="2:00")
        tk.Label(
            top,
            textvariable=timer_var,
            bg=self.flash_colors["bg"],
            fg="#d9534f",
            font=self.fonts["flash_title"],
        ).pack(side="right")
        tk.Label(
            top,
            text="⏱",
            bg=self.flash_colors["bg"],
            fg=self.flash_colors["muted"],
            font=self.fonts["subtitle"],
        ).pack(side="right", padx=(0, 4))

        def update_quiz_stats() -> None:
            current = min(index["value"] + 1, total_questions)
            elapsed = time.perf_counter() - start_time
            remaining = max(0, time_limit - elapsed)
            minutes = int(remaining) // 60
            seconds = int(remaining) % 60
            timer_var.set(f"{minutes}:{seconds:02d}")
            quiz_stats_var.set(f"Question {current}/{total_questions} | Score {score['value']}")

        def tick_timer() -> None:
            elapsed = time.perf_counter() - start_time
            remaining = max(0, time_limit - elapsed)
            minutes = int(remaining) // 60
            seconds = int(remaining) % 60
            timer_var.set(f"{minutes}:{seconds:02d}")
            if remaining <= 0:
                timer_var.set("0:00")
                finish_quiz()
                return
            timer_job["id"] = game.after(500, tick_timer)

        def style_default(button: tk.Button) -> None:
            button.configure(bg=self.flash_colors["panel_alt"], fg=self.flash_colors["text"], relief="raised", state="normal")

        def close_game() -> None:
            if auto_job["id"] is not None:
                try:
                    game.after_cancel(auto_job["id"])
                except Exception:
                    pass
                auto_job["id"] = None
            if timer_job["id"] is not None:
                try:
                    game.after_cancel(timer_job["id"])
                except Exception:
                    pass
                timer_job["id"] = None
            game.destroy()

        def finish_quiz() -> None:
            if timer_job["id"] is not None:
                try:
                    game.after_cancel(timer_job["id"])
                except Exception:
                    pass
                timer_job["id"] = None
            if auto_job["id"] is not None:
                try:
                    game.after_cancel(auto_job["id"])
                except Exception:
                    pass
                auto_job["id"] = None
            duration = max(0.0, time.perf_counter() - start_time)
            percentage = int(round((score["value"] / total_questions) * 100)) if total_questions else 0
            self.status_var.set(
                f"Quiz completed: {score['value']}/{total_questions} correct answers in {duration:.1f}s ({percentage}%)."
            )
            messagebox.showinfo(
                'Congratulations',
                f"You completed the quiz.\nScore: {score['value']}/{total_questions}\nAccuracy: {percentage}%\nTime: {duration:.1f}s",
            )
            close_game()

        def next_question() -> None:
            if auto_job["id"] is not None:
                try:
                    game.after_cancel(auto_job["id"])
                except Exception:
                    pass
                auto_job["id"] = None
            if not answered["value"]:
                return
            index["value"] += 1
            if index["value"] >= total_questions:
                finish_quiz()
                return
            render_question()

        def prev_question() -> None:
            if auto_job["id"] is not None:
                try:
                    game.after_cancel(auto_job["id"])
                except Exception:
                    pass
                auto_job["id"] = None
            if index["value"] <= 0:
                return
            index["value"] -= 1
            render_question()

        nav_row = tk.Frame(shell, bg=self.flash_colors["bg"])
        nav_row.pack(fill="x", pady=(8, 0))
        prev_button = self._flash_button(nav_row, '◀ Previous', prev_question, self.flash_colors["panel_alt"])
        prev_button.pack(side="left")
        next_button = self._flash_button(nav_row, 'Next ▶', next_question, self.flash_colors["accent"])
        next_button.pack(side="right")
        next_button.configure(state="disabled")

        def on_select(option_text: str, selected_button: tk.Button) -> None:
            if answered["value"]:
                return
            answered["value"] = True
            for button in option_buttons:
                button.configure(state="disabled")
            if option_text == current_answer["value"]:
                selected_button.configure(bg=match_green, fg="white")
                feedback_var.set('Correct! Nice work.')
                score["value"] += 1
                update_quiz_stats()
                if index["value"] >= total_questions - 1:
                    next_button.configure(text='Finish ▶', state="normal")
                else:
                    next_button.configure(text='Next ▶', state="normal")
                # Auto-advance after short delay on correct answer
                auto_job["id"] = game.after(900, next_question)
                return
            else:
                selected_button.configure(bg=mismatch_red, fg="white")
                feedback_var.set('Incorrect. The correct answer is highlighted in green.')
                for button in option_buttons:
                    if str(button.cget("text")) == current_answer["value"]:
                        button.configure(bg=match_green, fg="white")
                        break
            update_quiz_stats()
            if index["value"] >= total_questions - 1:
                next_button.configure(text='Finish ▶', state="normal")
            else:
                next_button.configure(text='Next ▶', state="normal")

        def build_options(correct_meaning: str, correct_key: str) -> list[str]:
            choices = [correct_meaning]
            distractors = [meaning for key, _word, meaning in pairs if key != correct_key and meaning != correct_meaning]
            random.shuffle(distractors)
            for meaning in distractors:
                if meaning in choices:
                    continue
                choices.append(meaning)
                if len(choices) == 4:
                    break
            if len(choices) < 4:
                for meaning in all_meanings:
                    if meaning in choices:
                        continue
                    choices.append(meaning)
                    if len(choices) == 4:
                        break
            random.shuffle(choices)
            return choices

        def render_question() -> None:
            if index["value"] >= total_questions:
                finish_quiz()
                return
            answered["value"] = False
            next_button.configure(state="disabled")
            feedback_var.set("")

            key, word, correct_meaning = question_bank[index["value"]]
            current_answer["value"] = correct_meaning
            word_var.set(self._uppercase_first_character(word))
            choices = build_options(correct_meaning, key)

            for btn_index, button in enumerate(option_buttons):
                if btn_index >= len(choices):
                    button.configure(text="", state="disabled")
                    continue
                choice_text = choices[btn_index]
                style_default(button)
                button.configure(
                    text=choice_text,
                    command=lambda value=choice_text, widget=button: on_select(value, widget),
                )
            update_quiz_stats()

        for _index in range(4):
            button = tk.Button(
                options_wrap,
                relief="raised",
                bd=1,
                padx=14,
                pady=14,
                anchor="w",
                justify="left",
                wraplength=760,
                bg=self.flash_colors["panel_alt"],
                fg=self.flash_colors["text"],
                activebackground=self.flash_colors["accent"],
                activeforeground="white",
                font=self.fonts["body"],
                cursor="hand2",
            )
            button.pack(fill="x", pady=(0, 10))
            option_buttons.append(button)

        control_row = tk.Frame(shell, bg=self.flash_colors["bg"])
        control_row.pack(fill="x")

        def start_new_quiz() -> None:
            close_game()
            self._quiz_flashcards()

        self._flash_button(control_row, 'New Round', start_new_quiz, self.flash_colors["panel_alt"]).pack(side="left")
        self._flash_button(control_row, 'Close', close_game, self.flash_colors["panel"]).pack(side="left", padx=(8, 0))

        game.protocol("WM_DELETE_WINDOW", close_game)
        render_question()
        tick_timer()


    def create_flashcard(self) -> None:
        default_front = self.current_lookup_word or self.lookup_word_var.get().strip()
        default_back = self._format_meaning_for_display(self.current_lookup_meaning) if self.current_lookup_meaning else ""
        self._open_flashcard_editor(Flashcard(front=default_front, back=default_back), original_front=None)

    def edit_current_flashcard(self) -> None:
        if not self.flashcard_words:
            messagebox.showwarning('Flashcards', 'No flashcard is selected.')
            return
        word = self.flashcard_words[self.flashcard_index]
        existing = self.flashcard_store.get(word)
        if existing is not None:
            self._open_flashcard_editor(existing, original_front=existing.front)
            return
        meaning = self.store.lookup(word) or ""
        self._open_flashcard_editor(Flashcard(front=word, back=self._format_meaning_for_display(meaning)), original_front=word)

    def delete_current_flashcard(self) -> None:
        if not self.flashcard_words:
            messagebox.showwarning('Flashcards', 'No flashcard is selected.')
            return
        word = self.flashcard_words[self.flashcard_index]
        if not self.flashcard_store.delete(word):
            messagebox.showinfo('Flashcards', 'This card only exists in dictionary data. Save as custom first if you want to delete it.')
            return
        self.status_var.set(f"Deleted custom flashcard '{word}'.")
        self._refresh_flashcards(reset=True)
        self._render_summary()
        self._update_stats()

    def save_current_word_as_flashcard(self) -> None:
        word = self.current_lookup_word or self.lookup_word_var.get().strip()
        if not word:
            messagebox.showwarning('Flashcards', 'Search a word first.')
            return
        word = self._uppercase_first_character(word)
        meaning = self.current_lookup_meaning or (self.store.lookup(word) or "")
        back = self._format_meaning_for_display(meaning)
        if not back:
            messagebox.showwarning('Flashcards', 'No meaning available to save.')
            return
        self.flashcard_store.upsert(word, back)
        self.flashcard_mode_var.set('Custom Cards')
        self._refresh_flashcards(reset=True)
        self._render_summary()
        self._update_stats()
        self.status_var.set(f"Saved '{word}' to custom cards.")

    def _open_flashcard_editor(self, card: Flashcard, original_front: str | None) -> None:
        editor = tk.Toplevel(self.root)
        editor.title('Flashcard Editor')
        editor.geometry("560x520")
        editor.configure(bg=self.colors["bg"])
        editor.transient(self.root)
        editor.grab_set()

        shell = tk.Frame(editor, bg=self.colors["surface"], padx=16, pady=16)
        shell.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(shell, text='Front', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["subtitle"]).pack(anchor="w")
        front_var = tk.StringVar(value=card.front)
        front_entry = tk.Entry(
            shell,
            textvariable=front_var,
            relief="flat",
            bd=0,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            font=self.fonts["body"],
        )
        front_entry.pack(fill="x", ipady=8, pady=(4, 10))

        tk.Label(shell, text='Back', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["subtitle"]).pack(anchor="w")
        back_widget = self._text_panel(shell, height=8)
        back_widget.pack(fill="x", pady=(4, 10))
        self._set_text_widget(back_widget, card.back)

        tk.Label(shell, text='Note (optional)', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["subtitle"]).pack(anchor="w")
        note_widget = self._text_panel(shell, height=5)
        note_widget.pack(fill="x", pady=(4, 10))
        self._set_text_widget(note_widget, card.note)

        tk.Label(shell, text='Tags (comma-separated)', bg=self.colors["surface"], fg=self.colors["text"], font=self.fonts["subtitle"]).pack(anchor="w")
        tags_var = tk.StringVar(value=", ".join(card.tags))
        tags_entry = tk.Entry(
            shell,
            textvariable=tags_var,
            relief="flat",
            bd=0,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            font=self.fonts["body"],
        )
        tags_entry.pack(fill="x", ipady=8, pady=(4, 12))

        actions = tk.Frame(shell, bg=self.colors["surface"])
        actions.pack(fill="x")

        def save_card() -> None:
            front = self._uppercase_first_character(front_var.get())
            back = self._get_text_widget(back_widget).strip()
            note = self._get_text_widget(note_widget).strip()
            tags = [part.strip() for part in tags_var.get().split(",") if part.strip()]
            try:
                if original_front and normalize_word(original_front) != normalize_word(front):
                    self.flashcard_store.delete(original_front)
                saved = self.flashcard_store.upsert(front, back, note=note, tags=tags)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror('Flashcards', str(exc))
                return
            self.status_var.set(f"Saved card '{saved.front}'.")
            self.flashcard_mode_var.set('Custom Cards')
            self._refresh_flashcards(reset=True)
            for index, word in enumerate(self.flashcard_words):
                if normalize_word(word) == normalize_word(saved.front):
                    self.flashcard_index = index
                    break
            self._render_flashcard()
            self._render_summary()
            self._update_stats()
            editor.destroy()

        self._action_button(actions, 'Save Card', save_card, self.colors["primary"]).pack(side="left")
        self._action_button(actions, 'Cancel', editor.destroy, self.colors["accent_alt"]).pack(side="left", padx=8)

    def open_current_flashcard(self) -> None:
        target = self.current_lookup_word or self.lookup_word_var.get().strip()
        if not target:
            return
        self._cancel_flashcard_transition()
        self.show_page("flashcards")
        self.flashcard_mode_var.set('All Words')
        deck = [target] + self.store.all_words() + self.flashcard_store.card_words()
        self.flashcard_words = self._unique_words(deck)
        self.flashcard_index = 0
        self.flashcard_answer_shown = False
        self._render_flashcard()

    def seed_assistant_prompt(self) -> None:
        prompt = 'Explain when to use this word, give clear examples, and warn about common mistakes.'
        self.assistant_question_text = prompt
        self._set_text_widget(self.assistant_input_widget, prompt)
        self.status_var.set('Seeded the assistant prompt with a study question.')

    def ask_assistant(self) -> None:
        question = self._get_text_widget(self.assistant_input_widget).strip()
        if not question:
            messagebox.showwarning('Assistant', 'Enter a question first.')
            return
        if not self.ai_client.enabled:
            messagebox.showwarning('Assistant', 'Gemini API key is not configured for the AI assistant.')
            return
        try:
            answer = self.ai_client.assistant_reply(question, word=self.current_lookup_word, meaning=self.current_lookup_meaning)
            context = self.current_lookup_word or 'general study'
            self.assistant_meta_var.set(f"Context: {context}")
            self.assistant_output_text = answer
            self._write_text(self.assistant_output_widget, self.assistant_output_text)
            self.status_var.set('Assistant response received.')
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('Assistant', str(exc))

    def run_benchmark(self) -> None:
        try:
            self._require_loaded()
            payload = run_all_benchmarks(self.store, self.store.paths.benchmark_json, lookup_sample_size=1000)
            self.bench_output_text = json.dumps(payload, ensure_ascii=False, indent=2)
            self._write_text(self.bench_output_widget, self.bench_output_text)
            self.status_var.set(f"Benchmark written to {self.store.paths.benchmark_json}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('Benchmark Error', str(exc))

    def run_profile_report(self) -> None:
        try:
            self._require_loaded()
            run_profile(self.store, self.store.paths.profile_txt)
            self.bench_output_text = self.store.paths.profile_txt.read_text(encoding="utf-8")
            self._write_text(self.bench_output_widget, self.bench_output_text)
            self.status_var.set(f"Profile written to {self.store.paths.profile_txt}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('Profile Error', str(exc))

    def _render_summary(self) -> None:
        if not self.current_lookup_word:
            self.summary_text = 'Search a word to view the Vietnamese meaning in the database.'
            self._write_text(self.summary_output, self.summary_text)
            return

        word_key = normalize_word(self.current_lookup_word)
        if not word_key:
            self.summary_text = 'No valid word found.'
            self._write_text(self.summary_output, self.summary_text)
            return

        vietnamese_meaning = self._get_vietnamese_meaning_from_database(word_key)
        display_word = self._uppercase_first_character(word_key)
        if vietnamese_meaning:
            self.summary_text = "\n\n".join([f"Word: {display_word}", f"Vietnamese Meaning:\n{vietnamese_meaning}"])
        else:
            self.summary_text = "\n\n".join(
                [
                    f"Word: {display_word}",
                    'No Vietnamese meaning is saved for this word in the local database.',
                ]
            )
        self._write_text(self.summary_output, self.summary_text)

    def _get_vietnamese_meaning_from_database(self, word_key: str) -> str:
        from_map = " ".join(self.vietnamese_meanings.get(word_key, "").split()).strip()
        if from_map:
            return from_map

        meaning_payload = self.store.lookup(word_key) or ""
        if meaning_payload:
            lines = self._extract_vietnamese_lines(meaning_payload)
            if lines:
                return "\n".join(lines[:4])

        # Fallback: fetch Vietnamese translation from online API in background
        def _fetch_translation():
            try:
                translated = self.translation_client.translate(word_key)
                if translated:
                    self.root.after(0, lambda: self._on_translation_done(word_key, translated))
            except Exception:
                pass
        threading.Thread(target=_fetch_translation, daemon=True).start()
        return ""

    def _on_translation_done(self, word_key: str, translated: str) -> None:
        """Handle Vietnamese translation result on the main thread."""
        self.vietnamese_meanings[word_key] = translated
        save_json(self.vietnamese_meaning_path, self.vietnamese_meanings)
        # Refresh summary if we're still looking at the same word
        if normalize_word(self.current_lookup_word) == word_key:
            self._render_summary()
            # Also update the home page Vietnamese panel if visible
            if self._home_results_visible and hasattr(self, '_home_vn_output'):
                self._write_text(self._home_vn_output, translated)


    @staticmethod
    def _extract_vietnamese_lines(meaning_payload: str) -> list[str]:
        prefixes = (
            "vi:",
            "vn:",
            "nghia:",
            "nghĩa:",
            'meaning:',
            "tieng viet:",
            "tiếng việt:",
            'vietnamese:',
            "dich:",
            "dịch:",
            'translation:',
        )
        excluded_prefixes = ("ipa:", "source:", "example:", "synonyms:", "antonyms:")
        lines: list[str] = []
        seen: set[str] = set()
        for raw_line in meaning_payload.splitlines():
            line = " ".join(raw_line.strip().split())
            if not line:
                continue
            lowered = line.lower()
            if lowered.startswith(excluded_prefixes):
                continue
            candidate = line
            has_vi_prefix = False
            for prefix in prefixes:
                if lowered.startswith(prefix):
                    has_vi_prefix = True
                    candidate = line[len(prefix) :].strip(" -:")
                    break
            if not candidate:
                continue
            if not has_vi_prefix and not VIETNAMESE_CHAR_RE.search(candidate):
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            lines.append(candidate)
        return lines

    def _update_stats(self) -> None:
        # Cache the audio file count to avoid slow glob on every stats update
        if self._audio_count_cache is None:
            try:
                self._audio_count_cache = len(list(self.store.paths.audio_cache_dir.glob('*.wav')))
            except Exception:
                self._audio_count_cache = 0
        self.stats_var.set(
            " | ".join(
                [
                    f"entries: {len(self.store.all_words())}",
                    f"due: {len(self.review_store.due_items())}",
                    f"cards: {len(self.flashcard_store.cards)}",
                    f"audio: {self._audio_count_cache}",
                    f"theme: {self.theme_var.get()}",
                    f"font: {self.font_size_var.get()}",
                ]
            )
        )

    def _push_search_panels(self) -> None:
        self._write_text(self.local_output, self.lookup_meaning_text)
        self._write_text(self.pronounce_output, self.pronounce_text)

    def _format_meaning_for_display(self, meaning: str) -> str:
        lines: list[str] = []
        seen: set[str] = set()
        for raw_line in meaning.splitlines():
            line = " ".join(raw_line.strip().split())
            lowered = line.lower()
            if not line:
                continue
            if lowered.startswith("ipa:") or lowered.startswith("source:") or lowered.startswith("example:"):
                continue
            if lowered.startswith("synonyms:") or lowered.startswith("antonyms:"):
                continue
            if line.startswith("[") and line.endswith("]"):
                continue
            if "usage notes" in lowered:
                continue
            prefix, separator, remainder = line.partition(". ")
            if separator and prefix.isdigit():
                line = remainder
            if line in seen:
                continue
            seen.add(line)
            lines.append(line)
        if not lines:
            return 'No clean definition has been saved yet.'
        return "\n\n".join(lines[:4])

    def _sync_pronunciation_cache(self, word: str, ipa: str) -> None:
        if ipa.strip():
            self.phonetics.set_ipa(word, ipa.strip())

    def _local_ipa_from_meaning(self, meaning: str) -> str:
        for raw_line in meaning.splitlines():
            line = raw_line.strip()
            if line.lower().startswith("ipa:"):
                return line.split(":", 1)[1].strip()
        return ""

    def _write_text(self, widget: ScrolledText | None, payload: object) -> None:
        if widget is None:
            return
        widget.delete("1.0", tk.END)
        if isinstance(payload, str):
            widget.insert(tk.END, payload)
        else:
            widget.insert(tk.END, json.dumps(payload, ensure_ascii=False, indent=2))

    def _write_flashcard_text(self, payload: str) -> None:
        widget = self.flashcard_output
        if widget is None:
            return
        widget.delete("1.0", tk.END)
        widget.insert("1.0", payload)
        widget.tag_configure("center", justify="center")
        widget.tag_add("center", "1.0", tk.END)

    def _set_text_widget(self, widget: ScrolledText | None, text: str) -> None:
        if widget is None:
            return
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)

    def _get_text_widget(self, widget: ScrolledText | None) -> str:
        if widget is None:
            return ""
        return widget.get("1.0", tk.END)

    def _require_loaded(self) -> None:
        if not self.store.hash_index:
            raise DataFileError("Dictionary data is missing. Click 'Init Demo Data' first or import data through the CLI.")

    def on_close(self) -> None:
        self._cancel_flashcard_transition()
        self.phonetics.stop_audio()
        self.store.close()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    app = DictionaryAppGUI()
    app.run()
    return 0
