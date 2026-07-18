"""Thai NLP backend + lexicon-based word segmentation.

Thai is an isolating language written WITHOUT spaces between words — the
two facts that shape everything here:

  - No inflection means lemmatize() is the identity: กิน is กิน whether
    it happened yesterday or will happen tomorrow (time rides on particles
    like แล้ว/จะ, which are separate vocabulary items).
  - No spaces means the generic regex tokenizer sees a whole clause as one
    "word". `segment()` does greedy longest-match against a lexicon (the
    frequency list), the standard baseline segmenter for Thai; unmatched
    spans come back as single unknown chunks so the sentence-difficulty
    scorer can count them.
"""
from __future__ import annotations

import re

from backend.services.nlp.base import BaseNLP

_THAI_RUN = re.compile(r"[฀-๿]+")

# Beyond this, a lexicon match is implausible and the scan wastes time.
_MAX_WORD_LEN = 24


def segment(text: str, lexicon: set[str]) -> list[str]:
    """Greedy longest-match segmentation of *text*'s Thai runs.

    Non-Thai spans (Latin words, digits, punctuation) are ignored — the
    caller handles them separately if it cares. Characters no lexicon word
    covers are grouped into single "unknown" chunks rather than dribbling
    out one char at a time.
    """
    out: list[str] = []
    for run in _THAI_RUN.findall(text):
        i = 0
        pending_unknown: list[str] = []
        while i < len(run):
            match = None
            for ln in range(min(_MAX_WORD_LEN, len(run) - i), 0, -1):
                cand = run[i:i + ln]
                if cand in lexicon:
                    match = cand
                    break
            if match:
                if pending_unknown:
                    out.append("".join(pending_unknown))
                    pending_unknown = []
                out.append(match)
                i += len(match)
            else:
                pending_unknown.append(run[i])
                i += 1
        if pending_unknown:
            out.append("".join(pending_unknown))
    return out


class ThaiNLP(BaseNLP):
    """Isolating language: identity lemmatizer, no diacritic folding."""

    def normalize(self, text: str) -> str:
        return text.strip().lower()

    def lemmatize(self, word: str) -> str:
        return word.strip().lower()

    def get_morphological_family(self, word: str) -> set[str]:
        return {word.strip().lower()}

    def get_aspect_partner(self, verb: str, card_context: dict | None = None) -> str | None:
        return None
