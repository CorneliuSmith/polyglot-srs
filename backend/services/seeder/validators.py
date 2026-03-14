"""Script and schema validation utilities for the CSV/TSV vocabulary importer."""
import re

# Character ranges for script validation
ARABIC_PATTERN = re.compile(
    r'^[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\s\u0640]+$'
)
CYRILLIC_PATTERN = re.compile(r'^[\u0400-\u04FF\u0500-\u052F\s\-]+$')
LATIN_PATTERN = re.compile(r"^[a-zA-Z\s\-']+$")

VALID_POS = {
    "noun", "verb", "adj", "adv", "particle",
    "preposition", "conjunction", "pronoun", "interjection",
}
VALID_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}

SCRIPT_VALIDATORS = {
    "ar": ("Arabic", ARABIC_PATTERN),
    "ru": ("Cyrillic", CYRILLIC_PATTERN),
    "en": ("Latin", LATIN_PATTERN),
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
