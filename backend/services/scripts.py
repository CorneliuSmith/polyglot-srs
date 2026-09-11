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
        return ["lower", "upper"]
    return ["letter"]


def alphabet_for(code: str | None) -> list[dict]:
    """The letters a course's stroke library covers, with the typing key
    and sound the alphabet decks already carry, and each letter's forms.
    A Latin-script course gets a–z; its own extra letters are a DEBT item."""
    script = script_of(code)
    rows = ALPHABETS.get(code or "", [])
    if not rows and script == "latin":
        rows = [(ch, ch, "") for ch in LATIN_BASE]
    return [{"glyph": g, "romanization": r, "sound": s, "forms": forms_for(script, g)}
            for g, r, s in rows]


def expected_forms(code: str | None) -> int:
    """How many (glyph, form) pairs a complete library for the course has,
    per style — the denominator of the Strokes panel's progress."""
    return sum(len(x["forms"]) for x in alphabet_for(code))
