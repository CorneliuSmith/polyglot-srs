"""
XhosaNLP backend — rule-based Nguni (Bantu) noun-class and verb morphology.

Xhosa-specific behaviour:
  - Normalization: lowercase + strip. Xhosa is written in plain ASCII Latin;
    the three click consonants are ordinary letters c (dental), q (palatal),
    x (lateral), so no special handling is needed.
  - Lemmatization: conservative verb concord stripping (subject concord +
    tense marker + stem, e.g. ndi-ya-hamba -> hamba). Only fires when both a
    subject concord and a tense marker are present, leaving nouns intact.
  - Morphological family: the verb stem plus common conjugations, and the
    noun-class singular/plural partner (umntu/abantu, isitya/izitya,
    inja/izinja, ...), so a plural typed for a singular grades CORRECT_SLOPPY.
  - No aspect-pair system — get_aspect_partner returns None.

Like Swahili, Xhosa has no production-grade open NLP library, so this backend
is deliberately rule-based and conservative.
"""
from __future__ import annotations

from backend.services.nlp.base import BaseNLP

# High-frequency subject concords (ordered longest-first).
_SUBJECT_CONCORDS = ("ndi", "ba", "si", "ni", "u", "a", "i")
# Tense/aspect markers that follow the subject concord.
_TENSE_MARKERS = ("ya", "za", "be", "sa")

_MIN_STEM_LEN = 3

# Noun-class singular -> plural prefix pairs (the regular subset). Some
# singulars (um-) belong to more than one class, so both partners are added;
# over-generation only ever softens a wrong answer to "sloppy", never the
# reverse.
_NOUN_CLASS_PAIRS = (
    ("aba", "um"),    # abantu  <- umntu (reverse handled below too)
    ("um", "aba"),    # umntu -> abantu (class 1/2, persons)
    ("um", "imi"),    # umthi -> imithi (class 3/4)
    ("umu", "imi"),
    ("ili", "ama"),   # ihashe/ilihashe -> amahashe (class 5/6)
    ("isi", "izi"),   # isitya -> izitya (class 7/8)
    ("in", "izin"),   # inja -> izinja (class 9/10)
    ("im", "izim"),
    ("ulu", "izin"),  # class 11
)


class XhosaNLP(BaseNLP):
    """Xhosa NLP backend (rule-based Nguni morphology)."""

    def normalize(self, text: str) -> str:
        """Lowercase and strip — plain Latin, clicks are ordinary letters."""
        return text.strip().lower()

    def lemmatize(self, word: str) -> str:
        """Strip subject-concord + tense-marker from conjugated verbs.

        Only strips when BOTH are present in sequence, keeping nouns intact:
            "ndiyahamba" -> "hamba"
            "bayadlala"  -> "dlala"
            "umntu"      -> "umntu"  (noun, untouched)
        """
        lowered = word.strip().lower()
        for subject in _SUBJECT_CONCORDS:
            if not lowered.startswith(subject):
                continue
            rest = lowered[len(subject):]
            for tense in _TENSE_MARKERS:
                if rest.startswith(tense):
                    stem = rest[len(tense):]
                    if len(stem) >= _MIN_STEM_LEN:
                        return stem
        return lowered

    def get_morphological_family(self, word: str) -> set[str]:
        """Return *word*, its verb stem + conjugations, and noun-class partner."""
        lowered = word.strip().lower()
        stem = self.lemmatize(lowered)
        family: set[str] = {lowered, stem}

        # Verb conjugations across common subject concords + present tense
        for subject in ("ndi", "u", "ba", "si"):
            for tense in ("ya", "za"):
                family.add(f"{subject}{tense}{stem}")

        # Noun-class singular/plural partners
        for prefix, partner in _NOUN_CLASS_PAIRS:
            if lowered.startswith(prefix) and len(lowered) > len(prefix) + 1:
                family.add(partner + lowered[len(prefix):])

        return family

    def get_aspect_partner(
        self,
        verb: str,
        card_context: dict | None = None,
    ) -> str | None:
        """Xhosa has no aspect-pair system — always returns None."""
        return None
