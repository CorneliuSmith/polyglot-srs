"""Which script a course writes in, which styles it is written in, and
which forms each letter takes — the shape of the stroke library that the
Workshop's Strokes panel authors and the guided Letters mode reads
(docs/plans/handwriting.md, §3, §5).

Forms are what a hand writes, not what a font shows: Arabic letters take
up to four positional forms (the six right-joining-only letters two);
cased scripts a lower and an upper; everything else one. Styles are the
hands a script is taught in: Russian print and cursive, Arabic a Naskh
hand first and ruqʿah later, Hebrew print and cursive (a different
alphabet), Latin print and cursive.
"""
from __future__ import annotations

from backend.services.seeder.seed_alphabet import ALPHABETS
from backend.services.write_coverage import NON_JOINING_LEFT

SCRIPT_OF: dict[str, str] = {
    "ru": "cyrillic", "el": "greek", "ar": "arabic", "fa": "arabic",
    "he": "hebrew", "hi": "devanagari", "th": "thai", "ko": "hangul",
}

STYLES: dict[str, list[str]] = {
    "cyrillic": ["cursive", "print"],
    "arabic": ["naskh", "ruqah"],
    "hebrew": ["cursive", "print"],
    "latin": ["print", "cursive"],
}

CASED = frozenset({"cyrillic", "greek", "latin"})

LATIN_BASE = [chr(c) for c in range(ord("a"), ord("z") + 1)]

# The letters a Latin-script course writes beyond a-z, in its own
# alphabet's order after the base. Only letters, not punctuation: Catalan's
# interpunct in l·l and Hausa's 'y are written as two marks, not as a glyph
# the Workshop can hold one stroke set for. A course not listed here writes
# a-z and nothing else (en, id, jam, sw, xh).
LATIN_EXTRAS: dict[str, list[str]] = {
    "ca": ["à", "ç", "è", "é", "í", "ï", "ò", "ó", "ú", "ü"],
    "de": ["ä", "ö", "ü", "ß"],
    "es": ["á", "é", "í", "ñ", "ó", "ú", "ü"],
    "fr": ["à", "â", "æ", "ç", "è", "é", "ê", "ë", "î", "ï",
           "ô", "œ", "ù", "û", "ü", "ÿ"],
    "ha": ["ɓ", "ɗ", "ƙ", "ƴ"],
    "it": ["à", "è", "é", "ì", "ò", "ó", "ù"],
    "la": ["ā", "ē", "ī", "ō", "ū"],
    "mi": ["ā", "ē", "ī", "ō", "ū"],
    "nl": ["é", "ë", "ï", "ö", "ü"],
    "pt": ["à", "á", "â", "ã", "ç", "é", "ê", "í", "ó", "ô", "õ", "ú"],
    "ro": ["ă", "â", "î", "ș", "ț"],
    "tl": ["ñ"],
    "tr": ["ç", "ğ", "ı", "ö", "ş", "ü"],
    "yo": ["ẹ", "ọ", "ṣ"],
}

# Letters in a cased script that no hand is taught an uppercase for. German
# ß has had a capital ẞ in Unicode since 2008 and in the official spelling
# rules since 2017, but schools still write SS and no copybook teaches the
# stroke order, so the library holds the lower form only. A list, not a
# frozenset, because the stroke generator reads this table by parsing this
# file (ast.literal_eval, no import) and a frozenset(...) call is not a
# literal.
CASELESS: list[str] = ["ß"]


def script_of(code: str | None) -> str:
    return SCRIPT_OF.get(code or "", "latin")


def styles_of(script: str) -> list[str]:
    return STYLES.get(script, ["print"])


def forms_for(script: str, glyph: str) -> list[str]:
    if script == "arabic":
        forms = ["isolated", "final"]
        if glyph not in NON_JOINING_LEFT:
            forms += ["initial", "medial"]
        return forms
    if script in CASED:
        return ["lower"] if glyph in CASELESS else ["lower", "upper"]
    return ["letter"]


def alphabet_for(code: str | None) -> list[dict]:
    """The letters a course's stroke library covers, with the typing key
    and sound the alphabet decks already carry, and each letter's forms.
    A Latin-script course gets a–z plus its own extras (LATIN_EXTRAS)."""
    script = script_of(code)
    rows = ALPHABETS.get(code or "", [])
    if not rows and script == "latin":
        extras = LATIN_EXTRAS.get(code or "", [])
        rows = [(ch, ch, "") for ch in LATIN_BASE + extras]
    return [{"glyph": g, "romanization": r, "sound": s, "forms": forms_for(script, g)}
            for g, r, s in rows]


def expected_forms(code: str | None) -> int:
    """How many (glyph, form) pairs a complete library for the course has,
    per style — the denominator of the Strokes panel's progress."""
    return sum(len(x["forms"]) for x in alphabet_for(code))
