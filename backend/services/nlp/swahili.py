"""
SwahiliNLP backend — rule-based Bantu verb-morphology handling.

Swahili-specific behaviour:
  - Normalization: lowercase + strip (plain Latin script, no diacritics).
  - Lemmatization: conservative verb-prefix stripping. Swahili verbs carry
    subject prefixes (ni-, u-, a-, tu-, m-, wa-) and tense/aspect markers
    (-na-, -li-, -ta-, -me-): "ninasoma" -> "soma" (read). Stripping only
    fires when both a subject prefix AND a tense marker are present, so
    ordinary nouns that happen to start with the same letters are untouched.
  - Morphological family: the verb stem plus common conjugations, and the
    noun-class plural partner from card morphology when provided
    (e.g. kitabu/vitabu is a ki-/vi- class pair the rules can derive).
  - No aspect-pair system — get_aspect_partner returns None.

No external NLP library exists for Swahili at the quality bar of pymorphy3 or
camel-tools, so this backend is fully rule-based by design.
"""
from __future__ import annotations

import logging

from backend.services.nlp.base import BaseNLP

logger = logging.getLogger(__name__)

# Subject prefixes (most common, ordered longest-first)
_SUBJECT_PREFIXES = ("wa", "ni", "tu", "u", "a", "m")

# Tense/aspect markers that follow the subject prefix
_TENSE_MARKERS = ("na", "li", "ta", "me", "ki", "hu")

_MIN_STEM_LEN = 3

# Noun-class singular -> plural prefix pairs (the regular subset)
_NOUN_CLASS_PAIRS = (
    ("ki", "vi"),   # kitabu -> vitabu
    ("m", "wa"),    # mtu -> watu (people class)
    ("m", "mi"),    # mti -> miti (tree class)
    ("ji", "ma"),   # jicho -> macho is irregular, but jino -> meno class regulars
)


class SwahiliNLP(BaseNLP):
    """Swahili NLP backend (rule-based Bantu morphology)."""

    def normalize(self, text: str) -> str:
        """Lowercase and strip — Swahili uses plain Latin with no diacritics."""
        return text.strip().lower()

    def lemmatize(self, word: str) -> str:
        """Strip subject-prefix + tense-marker from conjugated verbs.

        Only strips when BOTH a subject prefix and a tense marker are present
        in sequence ("ni" + "na" + stem), which keeps nouns intact:
            "ninasoma"  -> "soma"
            "alisoma"   -> "soma"
            "watasoma"  -> "soma"
            "kitabu"    -> "kitabu"  (no tense marker after "ki" + ... pattern)
        """
        lowered = word.strip().lower()
        for subject in _SUBJECT_PREFIXES:
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
        """Return *word*, its stem, common conjugations, and noun-class partner."""
        lowered = word.strip().lower()
        stem = self.lemmatize(lowered)
        family: set[str] = {lowered, stem}

        # Verb conjugations: present/past/future/perfect across common subjects
        if stem != lowered or lowered == stem:
            for subject in ("ni", "u", "a", "tu", "wa"):
                for tense in ("na", "li", "ta", "me"):
                    family.add(f"{subject}{tense}{stem}")

        # Noun-class plural/singular partner
        for singular, plural in _NOUN_CLASS_PAIRS:
            if lowered.startswith(singular) and len(lowered) > len(singular) + 1:
                family.add(plural + lowered[len(singular):])
            if lowered.startswith(plural) and len(lowered) > len(plural) + 1:
                family.add(singular + lowered[len(plural):])

        return family

    def get_aspect_partner(
        self,
        verb: str,
        card_context: dict | None = None,
    ) -> str | None:
        """Swahili has no aspect-pair system — always returns None."""
        return None
