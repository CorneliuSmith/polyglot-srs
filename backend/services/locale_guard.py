"""Does this text actually read in the language we are about to call it?

A learner studying Turkish with Arabic support was shown
"This city is very big and millions of people live there." under the
label الترجمة. The text was not wrong — it was English, served because no
Arabic rendering existed yet, and every layer downstream simply trusted
that whatever came back was in the requested locale.

Two different failures produce that screen, and only one of them is
visible in SQL:

  * MISSING — the locale row does not exist, so the query's COALESCE /
    `translation_locale IN (locale, 'en')` fallback serves English. The
    query knows; it just never said so, because the served locale was
    not selected into the payload.
  * MISLABELLED — a row exists FOR the locale and holds the wrong
    language anyway: an auto-translate pass that echoed its input, an
    import with the locale column defaulted, a hand-edit into the wrong
    row. No amount of locale tracking catches this one, because the
    database already believes it is Arabic.

This module catches both, by asking the only question that survives
either failure: is this text written in the script the locale uses?

That question has no answer for a Latin-script locale — "the book" and
"el libro" are the same script — so `script_of` returns None there and
`text_matches_locale` answers True rather than guessing. This guard is
deliberately one-sided: what it flags IS wrong, what it passes is merely
not provably wrong, and the served-locale field carried alongside it in
the payload covers the Latin-to-Latin case.
"""
from __future__ import annotations

import unicodedata

# Locale -> the script its prose is written in. Only locales whose script
# differs from Latin can be checked this way; everything else is absent on
# purpose and reads as "cannot tell".
_LOCALE_SCRIPT: dict[str, str] = {
    "ar": "ARABIC",
    "fa": "ARABIC",
    "ur": "ARABIC",
    "he": "HEBREW",
    "yi": "HEBREW",
    "ru": "CYRILLIC",
    "uk": "CYRILLIC",
    "bg": "CYRILLIC",
    "sr": "CYRILLIC",
    "el": "GREEK",
    "hi": "DEVANAGARI",
    "mr": "DEVANAGARI",
    "ne": "DEVANAGARI",
    "th": "THAI",
    "ko": "HANGUL",
    "ja": "HIRAGANA",   # kana carry the grammar; kanji alone is ambiguous
    "zh": "CJK",
    "hy": "ARMENIAN",
    "ka": "GEORGIAN",
    "am": "ETHIOPIC",
    "bn": "BENGALI",
    "ta": "TAMIL",
    "te": "TELUGU",
}

# Enough of the text must be in the expected script to call it that
# language. Well below half on purpose: a real translation can be mostly
# a quoted Latin name ("فيلم Titanic رائع") and must still pass, while
# fully-English prose scores zero and never squeaks through.
_MIN_SCRIPT_RATIO = 0.25


def script_of(locale: str | None) -> str | None:
    """The script *locale* is written in, or None when it cannot be used to
    tell languages apart (every Latin-script locale)."""
    if not locale:
        return None
    return _LOCALE_SCRIPT.get(locale.split("-")[0].strip().lower())


def _script_name(ch: str) -> str | None:
    """The script a single letter belongs to, by its Unicode name. Anything
    that is not a letter — digits, punctuation, spaces, emoji — has no
    script and is excluded from the ratio entirely, so "١٩٩١ ,." neither
    proves nor disproves anything."""
    if not ch.isalpha():
        return None
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return None
    first = name.split()[0]
    if first in ("HIRAGANA", "KATAKANA"):
        return "HIRAGANA"
    if first == "CJK":
        return "CJK"
    return first


def script_ratio(text: str, script: str) -> float:
    """Share of *text*'s letters that are written in *script* (0.0–1.0).
    Returns 0.0 for text with no letters at all."""
    letters = [s for s in (_script_name(c) for c in text) if s is not None]
    if not letters:
        return 0.0
    return sum(1 for s in letters if s == script) / len(letters)


def has_letters(text: str) -> bool:
    """Whether *text* contains anything a script could be read off. A date,
    a price or a lone dash does not."""
    return any(_script_name(c) for c in text)


def text_matches_locale(text: str | None, locale: str | None) -> bool:
    """True unless *text* is provably not written in *locale*.

    Three things pass without being checked, because none of them is
    evidence of the wrong language: empty text (that is a missing field,
    a different bug), text with no letters at all ("1991", "—"), and any
    Latin-script locale (indistinguishable by script).
    """
    if not text or not text.strip():
        return True
    script = script_of(locale)
    if script is None:
        return True
    if not has_letters(text):
        return True
    return script_ratio(text, script) >= _MIN_SCRIPT_RATIO


# The fields that are supposed to be in the LEARNER'S language.
# Deliberately not `sentence`, `correct_answer`, `gloss` or
# `transliteration`: those are in (or about) the language being studied,
# and checking them against the support locale would flag every card.
LOCALIZED_FIELDS = ("translation", "hint", "definition", "baseline")

# A personal cloze card's hint is its ANSWER — the learner's own word in
# the language they are studying (repositories/cards.py serves
# `cc.answer AS hint`, because a personal card carries no authored cue).
# Checking it against the support locale flags every personal card of
# every non-Latin learner, which is how this guard would have earned a
# reputation for crying wolf on its first day.
_FIELDS_BY_CARD_TYPE: dict[str, tuple[str, ...]] = {
    "personal": ("translation",),
}


def fields_for(card_type: str | None) -> tuple[str, ...]:
    return _FIELDS_BY_CARD_TYPE.get(card_type or "", LOCALIZED_FIELDS)


def mismatched_fields(
    card: dict, locale: str | None, fields: tuple[str, ...] | None = None
) -> list[str]:
    """Which of *card*'s learner-language fields are provably not in
    *locale*. Empty list is the normal case — including for every
    Latin-script locale, where this cannot be determined."""
    if script_of(locale) is None:
        return []
    checked = fields if fields is not None else fields_for(card.get("card_type"))
    return [
        f for f in checked
        if f in card and not text_matches_locale(card.get(f), locale)
    ]


def mark_locale_mismatches(card: dict, locale: str | None) -> dict:
    """Stamp a card with the fields that are not in the learner's language.

    Applied to the assembled payload rather than inside each query on
    purpose: one call covers vocabulary, grammar and personal cards, and
    it catches a row that merely CLAIMS to be in the locale — which no
    amount of tracking the served locale in SQL can do.

    The card is still served. The field is the learner's only semantic
    cue on a cloze, so withholding it would trade a card they can read
    the wrong language on for one they cannot answer at all; the UI
    labels it with the language it is actually in, and the existing
    demand queue fills it for next time. Absent key means "nothing to
    report", so older clients and every Latin-script locale see exactly
    what they saw before.
    """
    bad = mismatched_fields(card, locale)
    if bad:
        card["locale_mismatch"] = bad
    return card
