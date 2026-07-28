"""Script and schema validation utilities for the CSV/TSV vocabulary importer."""
import re

# Character ranges for script validation
ARABIC_PATTERN = re.compile(
    r'^[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\s\u0640]+$'
)
CYRILLIC_PATTERN = re.compile(r'^[\u0400-\u04FF\u0500-\u052F\s\-]+$')
LATIN_PATTERN = re.compile(r"^[a-zA-Z\s\-']+$")
# Devanagari block + extended, plus ZWNJ/ZWJ (conjunct control) and danda.
DEVANAGARI_PATTERN = re.compile(
    r'^[\u0900-\u097F\uA8E0-\uA8FF\u200C\u200D\s\-]+$'
)
THAI_PATTERN = re.compile(r'^[\u0E00-\u0E7F\s\-]+$')
# Hangul syllables + jamo blocks (compatibility jamo appear in letter names).
HANGUL_PATTERN = re.compile(
    r'^[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F\s\-]+$'
)
# Hebrew block (letters + niqqud + maqaf/geresh/gershayim all live in
# U+0590\u201305FF); apostrophe for loan sounds (\u05D2'\u05D9\u05E8\u05E4\u05D4).
HEBREW_PATTERN = re.compile(r"^[\u0590-\u05FF\s\-']+$")
# Persian: the Arabic ranges (\u067E \u0686 \u0698 \u06AF are inside U+0600\u201306FF) plus ZWNJ \u2014
# essential orthography (\u0645\u06CC\u200C\u0631\u0648\u0645), unlike Arabic where it never appears.
FARSI_PATTERN = re.compile(
    r'^[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF'
    r'\u200C\s\u0640]+$'
)

VALID_POS = {
    "noun", "verb", "adj", "adv", "particle",
    "preposition", "conjunction", "pronoun", "interjection",
}
VALID_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}
# How a word's CEFR level was decided (vocabulary.level_source). An optional CSV
# column: 'ai' marks a provisional, model-estimated level (gated until a reviewer
# confirms); absent lowers to the objective 'frequency' default.
VALID_LEVEL_SOURCES = {"frequency", "curated", "ai"}

SCRIPT_VALIDATORS = {
    "ar": ("Arabic", ARABIC_PATTERN),
    "ru": ("Cyrillic", CYRILLIC_PATTERN),
    "en": ("Latin", LATIN_PATTERN),
    "hi": ("Devanagari", DEVANAGARI_PATTERN),
    "th": ("Thai", THAI_PATTERN),
    "ko": ("Hangul", HANGUL_PATTERN),
    "he": ("Hebrew", HEBREW_PATTERN),
    "fa": ("Perso-Arabic", FARSI_PATTERN),
    # la/id/tl are Latin-script and deliberately unregistered, like es/fr/de:
    # the strict ASCII Latin check would reject legitimate diacritics
    # (Latin macrons ā/ē, Tagalog ñ), and unknown codes are always accepted.
}


class ValidationError:
    """Represents a single CSV validation failure."""

    def __init__(self, row: int, column: str, value: str, message: str):
        self.row = row
        self.column = column
        self.value = value
        self.message = message

    def __str__(self) -> str:
        return f"Row {self.row}, column '{self.column}': {self.message} (got: '{self.value}')"

    def __repr__(self) -> str:  # pragma: no cover
        return f"ValidationError({self!s})"


def validate_script(word: str, language_code: str) -> str | None:
    """Return an error message if *word* uses the wrong script, else None.

    Only languages registered in SCRIPT_VALIDATORS are checked; unknown
    language codes are always accepted.
    """
    if language_code not in SCRIPT_VALIDATORS:
        return None
    script_name, pattern = SCRIPT_VALIDATORS[language_code]
    clean = word.strip()
    if not clean:
        return "word is empty"
    if not pattern.match(clean):
        return f"word contains non-{script_name} characters"
    return None
