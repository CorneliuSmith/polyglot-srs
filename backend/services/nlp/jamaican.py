"""Jamaican Patois (Patwa) NLP backend.

Patois has no single standard orthography in everyday use: the app teaches
the Cassidy/JLU (Jamaican Language Unit) phonemic spelling, but most writing
in the wild uses ad-hoc English-based spellings ("mi a go" vs "me a guh").
Grading must not fail a learner for picking the other convention, so
normalization folds both toward a shared phonemic skeleton:

  - English-based digraphs -> Cassidy equivalents (ou->ow, th->t/d is NOT
    folded — /t/ vs /d/ is contrastive; we only fold spelling variants that
    are pronounced identically)
  - doubled consonants collapse, final silent -e drops ("gwaan"=="gwan"
    stays distinct from "gwane" folding)

Vocabulary rows also carry the common English-based spelling as an answer
alternative, so the folding here is a safety net, not the primary path.
Draft tier: everything ships reviewed:false until the JLU-connected
reviewer pass (beta rollout plan).
"""
from __future__ import annotations

import re

from backend.services.nlp.base import BaseNLP

# Spelling-variant folds that do not change pronunciation. Ordered, applied
# to lowercase text.
_FOLDS: list[tuple[str, str]] = [
    ("ough", "o"),      # though -> tho spellings
    ("gh", ""),         # right/rite class
    ("ck", "k"),
    ("ph", "f"),
    ("qu", "kw"),
    ("ou", "ow"),       # bout/bowt
    ("oo", "u"),        # good/gud
    ("ea", "ii"),       # deal/diil
    ("ee", "ii"),       # see/sii
    ("ai", "ie"),       # wait/wiet (Cassidy ie)
    ("ay", "ie"),
    ("c", "k"),         # hard c; Cassidy uses k throughout
    ("y", "i"),         # word-internal y/i variance; final -y handled below
]


def _fold(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"e\b", "", t)             # final silent -e
    for a, b in _FOLDS:
        t = t.replace(a, b)
    t = re.sub(r"(.)\1+", r"\1", t)       # collapse doubled letters
    return t


class JamaicanNLP(BaseNLP):
    """Spelling-tolerant Patois backend (Cassidy/JLU primary orthography)."""

    def normalize(self, text: str) -> str:
        return text.strip().lower()

    def lemmatize(self, word: str) -> str:
        # Patois is highly isolating — no inflectional morphology to strip
        # (tense/aspect ride on particles: did, a, gwaan). Fold spelling only.
        return _fold(word)

    def get_morphological_family(self, word: str) -> set[str]:
        w = word.strip().lower()
        return {w, _fold(w)}

    def get_aspect_partner(self, verb: str, card_context: dict | None = None) -> str | None:
        return None
