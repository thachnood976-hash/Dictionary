"""Comprehensive offline grammar checking engine.

Checks for common English grammar mistakes and suggests corrections,
following formal English rules.  Each rule produces structured issues
with ``{start, end, original, suggestion, reason}`` dictionaries that
the GUI can render as highlighted errors.
"""
from __future__ import annotations

import difflib
import re
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_case(original: str, suggestion: str) -> str:
    """Preserve the case pattern of *original* while applying *suggestion*."""
    if not original:
        return suggestion
    if original.isupper():
        return suggestion.upper()
    if original[0].isupper():
        return suggestion.capitalize()
    return suggestion


_TOKEN_RE = re.compile(r"[A-Za-z']+")

# Words that begin with a vowel letter but use "a" (consonant sound)
_A_BEFORE_VOWEL_EXCEPTIONS = {
    "university", "uniform", "unique", "united", "union", "unit",
    "universal", "use", "used", "useful", "user", "usual", "usually",
    "unicorn", "uranium", "utensil", "utility", "one", "once",
    "european",
}

# Words that begin with a consonant letter but use "an" (vowel sound)
_AN_BEFORE_CONSONANT_EXCEPTIONS = {
    "hour", "hours", "honest", "honor", "honour", "heir", "herb",
    "homage",
}

# Common confusable pairs: wrong -> correct keyed by context
_CONFUSABLES: dict[str, list[tuple[str, str, str]]] = {
    # (wrong, correction, reason)
    "your":   [("you're", "before an adjective/adverb", "your")],
    "you're": [("your",   "before a noun (possessive)", "you're")],
    "their":  [("there",  "'there' indicates a place", "their"),
               ("they're","'they're' = they are", "their")],
    "there":  [("their",  "'their' is possessive", "there")],
    "they're":[("their",  "'their' is possessive", "they're")],
    "its":    [("it's",   "'it's' = it is / it has", "its")],
    "it's":   [("its",    "'its' is possessive", "it's")],
    "then":   [("than",   "'than' is for comparisons", "then")],
    "than":   [("then",   "'then' is for sequence/time", "than")],
    "affect": [("effect", "'effect' is usually a noun", "affect")],
    "effect": [("affect", "'affect' is usually a verb", "effect")],
    "to":     [("too",    "'too' means also/excessively", "to")],
    "too":    [("to",     "'to' is a preposition/infinitive marker", "too")],
    "loose":  [("lose",   "'lose' means to misplace", "loose")],
    "lose":   [("loose",  "'loose' means not tight", "lose")],
    "accept": [("except", "'except' means excluding", "accept")],
    "except": [("accept", "'accept' means to receive", "except")],
    "alot":   [("a lot",  "'a lot' is two words", "alot")],
    "definately": [("definitely", "Correct spelling", "definately")],
    "seperate":   [("separate", "Correct spelling", "seperate")],
    "occured":    [("occurred", "Correct spelling: double 'r'", "occured")],
    "recieve":    [("receive",  "Correct spelling: i before e after c", "recieve")],
    "beleive":    [("believe",  "Correct spelling: ie not ei", "beleive")],
    "wierd":      [("weird",    "Correct spelling", "wierd")],
    "goverment":  [("government","Correct spelling", "goverment")],
    "enviroment": [("environment","Correct spelling", "enviroment")],
    "wich":       [("which",    "Correct spelling", "wich")],
    "becuase":    [("because",  "Correct spelling", "becuase")],
    "untill":     [("until",    "Correct spelling: single 'l'", "untill")],
    "teh":        [("the",      "Correct spelling", "teh")],
    "thier":      [("their",    "Correct spelling", "thier")],
    "dont":       [("don't",    "Missing apostrophe", "dont")],
    "doesnt":     [("doesn't",  "Missing apostrophe", "doesnt")],
    "didnt":      [("didn't",   "Missing apostrophe", "didnt")],
    "isnt":       [("isn't",    "Missing apostrophe", "isnt")],
    "arent":      [("aren't",   "Missing apostrophe", "arent")],
    "wasnt":      [("wasn't",   "Missing apostrophe", "wasnt")],
    "werent":     [("weren't",  "Missing apostrophe", "werent")],
    "wont":       [("won't",    "Missing apostrophe", "wont")],
    "cant":       [("can't",    "Missing apostrophe", "cant")],
    "shouldnt":   [("shouldn't","Missing apostrophe", "shouldnt")],
    "wouldnt":    [("wouldn't", "Missing apostrophe", "wouldnt")],
    "couldnt":    [("couldn't", "Missing apostrophe", "couldnt")],
    "hasnt":      [("hasn't",   "Missing apostrophe", "hasnt")],
    "havent":     [("haven't",  "Missing apostrophe", "havent")],
    "hadnt":      [("hadn't",   "Missing apostrophe", "hadnt")],
    "aint":       [("ain't",    "Missing apostrophe (informal)", "aint")],
    "im":         [("I'm",      "Missing apostrophe", "im")],
    "ive":        [("I've",     "Missing apostrophe", "ive")],
    "id":         [("I'd",      "Missing apostrophe (ambiguous)", "id")],
    "ill":        [("I'll",     "Missing apostrophe (could also mean 'sick')", "ill")],
    "hes":        [("he's",     "Missing apostrophe", "hes")],
    "shes":       [("she's",    "Missing apostrophe", "shes")],
    "whos":       [("who's",    "Missing apostrophe", "whos")],
    "thats":      [("that's",   "Missing apostrophe", "thats")],
    "whats":      [("what's",   "Missing apostrophe", "whats")],
    "lets":       [("let's",    "Missing apostrophe (if 'let us')", "lets")],
}

# Redundant expressions
_REDUNDANCIES: dict[str, tuple[str, str]] = {
    "atm machine":       ("ATM",             "'ATM' already means 'Automated Teller Machine'."),
    "pin number":        ("PIN",             "'PIN' already means 'Personal Identification Number'."),
    "very unique":       ("unique",          "'Unique' is already absolute; no modifier needed."),
    "most unique":       ("unique",          "'Unique' is already absolute; no modifier needed."),
    "completely unique": ("unique",          "'Unique' is already absolute; no modifier needed."),
    "past history":      ("history",         "'History' already refers to the past."),
    "free gift":         ("gift",            "A 'gift' is inherently free."),
    "end result":        ("result",          "'Result' already implies an end."),
    "added bonus":       ("bonus",           "A 'bonus' is already extra."),
    "close proximity":   ("proximity",       "'Proximity' already means close."),
    "each and every":    ("each",            "Use 'each' or 'every', not both."),
    "first and foremost":("first",           "'First' is sufficient."),
    "basic fundamentals":("fundamentals",    "'Fundamentals' are already basic."),
    "true fact":         ("fact",            "A 'fact' is inherently true."),
    "advance planning":  ("planning",        "'Planning' is done in advance."),
    "repeat again":      ("repeat",          "'Repeat' already means to do again."),
    "revert back":       ("revert",          "'Revert' already means to go back."),
    "return back":       ("return",          "'Return' already means to go back."),
}

# Subject-verb agreement lookup
_SINGULAR_SUBJECTS = {"he", "she", "it"}
_PLURAL_SUBJECTS   = {"you", "we", "they"}

# Irregular past tenses for common verbs (base -> past)
_COMMON_PAST_FORMS: dict[str, str] = {
    "go": "went", "goes": "went",
    "do": "did",  "does": "did",
    "have": "had", "has": "had",
    "is": "was",  "are": "were",
    "come": "came", "comes": "came",
    "see": "saw",  "sees": "saw",
    "take": "took", "takes": "took",
    "make": "made", "makes": "made",
    "give": "gave", "gives": "gave",
    "know": "knew", "knows": "knew",
    "get": "got",  "gets": "got",
    "say": "said", "says": "said",
    "run": "ran",  "runs": "ran",
    "eat": "ate",  "eats": "ate",
    "write": "wrote", "writes": "wrote",
    "speak": "spoke", "speaks": "spoke",
    "think": "thought", "thinks": "thought",
    "buy": "bought", "buys": "bought",
    "bring": "brought", "brings": "brought",
    "teach": "taught", "teaches": "taught",
    "catch": "caught", "catches": "caught",
    "feel": "felt", "feels": "felt",
    "find": "found", "finds": "found",
    "hear": "heard", "hears": "heard",
    "keep": "kept", "keeps": "kept",
    "leave": "left", "leaves": "left",
    "meet": "met", "meets": "met",
    "read": "read", "reads": "read",
    "send": "sent", "sends": "sent",
    "sit": "sat", "sits": "sat",
    "stand": "stood", "stands": "stood",
    "tell": "told", "tells": "told",
    "win": "won", "wins": "won",
}


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_grammar(
    sentence: str,
    vocabulary: set[str] | None = None,
    candidates: list[str] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Analyze *sentence* for grammar issues.

    Returns ``(issues, corrected_sentence)`` where each issue is a dict
    with keys ``start``, ``end``, ``original``, ``suggestion``, ``reason``.
    """
    token_matches = list(_TOKEN_RE.finditer(sentence))
    tokens = [(m.group(0), m.start(), m.end()) for m in token_matches]
    issues: list[dict[str, Any]] = []
    seen_spans: set[tuple[int, int]] = set()

    vocab = vocabulary or set()
    lookups = candidates or sorted(vocab)

    def add(start: int, end: int, original: str, suggestion: str, reason: str, *, override: bool = False) -> None:
        if not suggestion or suggestion == original:
            return
        span = (start, end)
        if span in seen_spans:
            if not override:
                return
            # Remove the previous issue for this span so we can replace it
            issues[:] = [i for i in issues if (int(i['start']), int(i['end'])) != span]
        seen_spans.add(span)
        issues.append({
            "start": start, "end": end,
            "original": original, "suggestion": suggestion,
            "reason": reason,
        })

    # Track whether the first word needs capitalization (applied later)
    first_needs_cap = False
    if tokens:
        first_tok, first_s, first_e = tokens[0]
        if first_tok[0].islower():
            first_needs_cap = True

    for idx, (token, start, end) in enumerate(tokens):
        lower = token.lower()
        prev = tokens[idx - 1][0].lower() if idx > 0 else ""
        nxt  = tokens[idx + 1][0].lower() if idx + 1 < len(tokens) else ""

        # ------------------------------------------------------------------
        # 2. Pronoun "I" always uppercase
        # ------------------------------------------------------------------
        if lower == "i" and token != "I":
            add(start, end, token, "I", "Pronoun 'I' should always be uppercase.")

        # ------------------------------------------------------------------
        # 3. Subject-verb agreement
        # ------------------------------------------------------------------
        if prev == "i" and lower in {"is", "are", "was", "were"}:
            add(start, end, token, _apply_case(token, "am"), "Use 'am' after 'I'.")
            continue
        if prev in _SINGULAR_SUBJECTS and lower in {"are", "were", "have", "do"}:
            fix_map = {"are": "is", "were": "was", "have": "has", "do": "does"}
            add(start, end, token, _apply_case(token, fix_map[lower]),
                f"Use '{fix_map[lower]}' with {prev}.")
            continue
        if prev in _PLURAL_SUBJECTS and lower in {"is", "was", "has", "does"}:
            fix_map = {"is": "are", "was": "were", "has": "have", "does": "do"}
            add(start, end, token, _apply_case(token, fix_map[lower]),
                f"Use '{fix_map[lower]}' with {prev}.")
            continue

        # ------------------------------------------------------------------
        # 4. Article a/an (override capitalization if needed)
        # ------------------------------------------------------------------
        if lower == "a" and nxt:
            if nxt in _AN_BEFORE_CONSONANT_EXCEPTIONS or (
                nxt[0] in "aeiou" and nxt not in _A_BEFORE_VOWEL_EXCEPTIONS
            ):
                add(start, end, token, _apply_case(token, "an"),
                    "Use 'an' before vowel sounds.", override=True)
        if lower == "an" and nxt:
            if nxt in _A_BEFORE_VOWEL_EXCEPTIONS or (
                nxt[0] not in "aeiou" and nxt not in _AN_BEFORE_CONSONANT_EXCEPTIONS
            ):
                add(start, end, token, _apply_case(token, "a"),
                    "Use 'a' before consonant sounds.", override=True)

        # ------------------------------------------------------------------
        # 5. Tense after "did" — should be base form
        # ------------------------------------------------------------------
        if prev == "did" and lower in _COMMON_PAST_FORMS.values():
            # Find the base form
            for base, past in _COMMON_PAST_FORMS.items():
                if past == lower and base != lower:
                    add(start, end, token, _apply_case(token, base),
                        f"After 'did', use base form '{base}' instead of '{lower}'.")
                    break

        # ------------------------------------------------------------------
        # 6. Double negatives — look back up to 4 tokens for negation
        # ------------------------------------------------------------------
        if lower in {"no", "nothing", "nobody", "nowhere", "never", "none"}:
            has_prior_neg = False
            lookback = min(idx, 4)
            for back in range(1, lookback + 1):
                prev_tok = tokens[idx - back][0].lower()
                if prev_tok in {"not", "no", "never", "neither", "nor"} or prev_tok.endswith("n't"):
                    has_prior_neg = True
                    break
            if has_prior_neg:
                fix = {"no": "any", "nothing": "anything", "nobody": "anybody",
                       "nowhere": "anywhere", "never": "ever", "none": "any"}
                if lower in fix:
                    add(start, end, token, _apply_case(token, fix[lower]),
                        f"Avoid double negatives. Use '{fix[lower]}' instead.",
                        override=True)

        # ------------------------------------------------------------------
        # 7. Common confusables & misspellings
        # ------------------------------------------------------------------
        if lower in _CONFUSABLES:
            entries = _CONFUSABLES[lower]
            # Simple heuristic-based context detection
            for correction, context_hint, _wrong in entries:
                # "your" before adjective/adverb -> should be "you're"
                if lower == "your" and nxt in {
                    "very", "really", "so", "too", "quite", "extremely",
                    "smart", "beautiful", "great", "nice", "good", "bad",
                    "right", "wrong", "welcome", "amazing", "awesome",
                    "stupid", "crazy", "funny", "kind", "sweet",
                    "wonderful", "terrible", "horrible", "incredible",
                    "late", "early", "tall", "short", "old", "young",
                    "happy", "sad", "angry", "tired", "sick", "ready",
                    "sure", "correct", "perfect", "brilliant",
                }:
                    add(start, end, token, _apply_case(token, "you're"),
                        "Use 'you're' (you are) before an adjective.",
                        override=True)
                    break
                # "its" before a verb -> should be "it's"
                if lower == "its" and nxt in {
                    "a", "an", "the", "my", "your", "his", "her", "our", "their",
                    "not", "very", "really", "so", "been", "going", "getting",
                }:
                    add(start, end, token, "it's",
                        "Use 'it's' (it is / it has) here.",
                        override=True)
                    break
                # "then" used in comparison -> should be "than"
                if lower == "then" and prev in {
                    "more", "less", "better", "worse", "greater", "smaller",
                    "bigger", "taller", "shorter", "faster", "slower",
                    "harder", "easier", "longer", "higher", "lower",
                    "rather", "other",
                }:
                    add(start, end, token, _apply_case(token, "than"),
                        "Use 'than' for comparisons.",
                        override=True)
                    break
                # Missing apostrophes (direct fix -- always apply)
                if "apostrophe" in context_hint.lower() or "Missing apostrophe" in context_hint:
                    add(start, end, token, correction,
                        context_hint, override=True)
                    break
                # Direct misspellings (always apply)
                if "Correct spelling" in context_hint:
                    add(start, end, token, correction,
                        context_hint, override=True)
                    break

        # ------------------------------------------------------------------
        # 8. Spelling via vocabulary (existing behavior, enhanced)
        # ------------------------------------------------------------------
        if not vocab or len(lower) <= 2:
            continue
        if lower in vocab:
            continue
        if lower in _CONFUSABLES:
            continue  # already handled
        if token[0].isupper():
            continue
        close = difflib.get_close_matches(lower, lookups, n=1, cutoff=0.84)
        if close:
            add(start, end, token, _apply_case(token, close[0]),
                "Possible spelling mistake.")

    # ------------------------------------------------------------------
    # 9. Redundancy check (multi-word patterns)
    # ------------------------------------------------------------------
    lower_sentence = sentence.lower()
    for pattern, (replacement, reason) in _REDUNDANCIES.items():
        pos = lower_sentence.find(pattern)
        while pos != -1:
            pend = pos + len(pattern)
            span = (pos, pend)
            if span not in seen_spans:
                original_text = sentence[pos:pend]
                seen_spans.add(span)
                issues.append({
                    "start": pos, "end": pend,
                    "original": original_text, "suggestion": replacement,
                    "reason": reason,
                })
            pos = lower_sentence.find(pattern, pend)

    # ------------------------------------------------------------------
    # 10. Punctuation — sentence should end with . ? !
    # ------------------------------------------------------------------
    stripped = sentence.rstrip()
    if stripped and stripped[-1] not in ".?!":
        # Only flag if it looks like a real sentence (has at least 3 words)
        if len(tokens) >= 3:
            issues.append({
                "start": len(stripped), "end": len(stripped),
                "original": "", "suggestion": ".",
                "reason": "Sentences should end with punctuation (. ? !).",
            })

    # If first word still needs capitalization and has no override issue, add it
    if first_needs_cap and tokens:
        first_tok, first_s, first_e = tokens[0]
        span = (first_s, first_e)
        if span not in seen_spans:
            add(first_s, first_e, first_tok, first_tok.capitalize(),
                "Capitalize the first word of a sentence.")
        else:
            # Capitalize the suggestion of whatever issue overrode it
            for issue in issues:
                if int(issue['start']) == first_s and int(issue['end']) == first_e:
                    sug = str(issue['suggestion'])
                    if sug and sug[0].islower():
                        issue['suggestion'] = sug[0].upper() + sug[1:]
                    break

    # Build corrected sentence
    issues.sort(key=lambda i: int(i["start"]))
    corrected_parts: list[str] = []
    cursor = 0
    for issue in issues:
        s = int(issue["start"])
        e = int(issue["end"])
        suggestion = str(issue["suggestion"])
        if s < cursor:
            continue
        corrected_parts.append(sentence[cursor:s])
        corrected_parts.append(suggestion)
        cursor = e
    corrected_parts.append(sentence[cursor:])
    corrected = "".join(corrected_parts)

    return issues, corrected
