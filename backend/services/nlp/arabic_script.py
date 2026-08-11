"""
Look-alike letter folding for the Arabic script (Arabic and Persian).

The problem this exists for: a learner types an answer on a phone, sees it
render exactly like the expected answer, and is marked wrong. Copy-pasting
the same word passes. Nothing in the six grading layers explained it, because
the difference isn't a mistake the learner made — it's which codepoint their
keyboard happened to emit.

Three families cause it:

  * **Yeh.** Arabic ends many words in alef maqsura ى (U+0649) — إلى, على.
    Phone keyboards give ي (U+064A) far more readily, Egyptian usage writes
    ي for both, and a Persian keyboard emits a third character, ی (U+06CC),
    that looks like either. All three are visually the same dotless-or-dotted
    tail at the end of a word.
  * **Kaf.** Persian keheh ک (U+06A9) and Arabic kaf ك (U+0643) are the same
    letter to a reader. Anyone typing Persian on an Arabic keyboard — the
    common case, since iOS ships Arabic by default — produces the wrong one
    in every single word containing it.
  * **Presentation forms.** Text copied out of some PDFs and older sites
    carries the U+FB50–U+FEFF contextual glyphs instead of the base letters.
    NFC leaves those alone (only NFKC folds them), so they compared unequal.

Folding is deliberately NOT part of normalize(): these are distinct letters
and a learner should eventually spell them right. It feeds a coaching layer,
so a folded match still surfaces "check the letter forms" — accepted, but
named. Taa marbuta ة/ه sits here for the same reason it is kept out of
normalize (research pitfall #6): conflating them outright would merge real
words, but declining to grade it at all failed people over an invisible-to-
them distinction.
"""
from __future__ import annotations

import re
import unicodedata

# Every yeh-shaped letter → Arabic yeh. Alef maqsura, Farsi yeh, and the
# Urdu/Kashmiri variants all end up in the same bucket.
_YEH = "ىیيېےٸ"
# Every kaf-shaped letter → Arabic kaf.
_KAF = "کكڪګڬڭڮ"
# Heh-shaped: taa marbuta and the Persian/Urdu hehs.
_HEH = "ةهۀہۂۃە"
# Alef-shaped (normalize already folds most of these for Arabic; Persian's
# backend does not, so the fold has to carry them itself).
_ALEF = "آأإٱٲٳا"

_FOLD_MAP = {
    **{ord(c): "ي" for c in _YEH},
    **{ord(c): "ك" for c in _KAF},
    **{ord(c): "ه" for c in _HEH},
    **{ord(c): "ا" for c in _ALEF},
    # Hamza carriers: which seat the hamza takes is a spelling rule learners
    # get wrong long before it means they don't know the word.
    ord("ؤ"): "و",  # ؤ → و
    ord("ئ"): "ي",  # ئ → ي
    # Standalone hamza dropped entirely: learners omit word-final ء (سما for
    # سماء) long before it means they don't know the word — same accept-and-
    # coach treatment as the seated hamzas above.
    ord("ء"): "",
    ord("ـ"): "",        # tatweel (kashida) — pure decoration
}

# Arabic-Indic (٠-٩) and Eastern Arabic-Indic (۰-۹) digits → ASCII. A phone
# switched to an Arabic locale types the former; the seeded answers use the
# latter, or plain ASCII, with no consistency a learner could follow.
_DIGITS = {
    **{0x0660 + i: str(i) for i in range(10)},
    **{0x06F0 + i: str(i) for i in range(10)},
}

_TASHKEEL = re.compile(r"[ً-ْٰٓ-ٟۖ-ۭ]")


def fold_arabic_script(text: str) -> str:
    """Collapse visually-equivalent Arabic-script codepoints.

    NFKC first (folds the U+FB50–U+FEFF presentation forms back to base
    letters), then the look-alike map, then harakat — Persian's backend folds
    combining marks generically, but the presentation forms can reintroduce
    them, so they come off after the fold rather than before.
    """
    folded = unicodedata.normalize("NFKC", text)
    folded = folded.translate(_FOLD_MAP).translate(_DIGITS)
    return _TASHKEEL.sub("", folded)
