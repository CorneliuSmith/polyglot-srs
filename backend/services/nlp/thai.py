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

import csv
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from backend.services.nlp.base import BaseNLP

logger = logging.getLogger(__name__)

_DATA = Path(__file__).resolve().parents[3] / "data"

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


def _is_word(entry: str) -> bool:
    """Reject lexicon entries that are not words.

    `data/th_frequency.tsv` carries 22 headwords that are a single Thai
    letter or a bare tone mark — `แ`, `โ`, `ณ`, `เ`, `ร`, `้`, `า` — 16 of
    them inside the top 2,000 (DEBT.md). A single character cannot be a Thai
    word: the script builds a syllable from a consonant plus its vowel, so
    these are fragments of the writing system rather than vocabulary.

    Keeping them out matters twice over. They let greedy longest-match
    "parse" a run it does not understand — `ทอมเป็นลูกบุญธรรม` came back as
    three real words plus `บุ ญ ธ ร ร ม`, every one of them "known", so a
    clean-parse check waved it through and a length check called it nine
    words. And they let `answer_span` blank a letter as if it were a word.
    """
    if len(entry) < 2:
        return False
    return any(unicodedata.category(ch).startswith("L") for ch in entry)


@lru_cache(maxsize=1)
def cloze_lexicon() -> frozenset[str]:
    """Every string this course treats as a Thai word.

    The union of the frequency list and the readings table, because the two
    disagree in both directions and each half earns its place: measured over
    the 4,024 sentences `make_cloze` could not blank, the readings table
    alone segmented 91% of them so that the headword fell out as a word, the
    frequency list alone 99% — but the frequency list's extra hits are junk
    headwords (single letters and a tone mark, `แ` `่` `า` `ร` `ั`) matching
    stray characters, which the clean-parse rule in `answer_span` throws out.
    The union with that rule keeps 3,347 and rejects the mis-parses.

    Degrades to empty when the files are unreadable: `answer_span` then finds
    nothing and the card falls back to the definition prompt, which is what
    it did for every Thai card before this existed.
    """
    words: set[str] = set()
    for name, column in (("th_frequency.tsv", "word"), ("th_readings.tsv", "word")):
        try:
            with (_DATA / name).open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle, delimiter="\t"):
                    word = (row.get(column) or "").strip()
                    if _is_word(word):
                        words.add(word)
        except OSError as exc:  # noqa: BLE001 — a missing file must never 500
            logger.warning("thai lexicon %s unavailable: %s", name, exc)
    return frozenset(words)


def answer_span(sentence: str, answer: str) -> tuple[int, int] | None:
    """Where *answer* sits in *sentence* as a standalone WORD, or None.

    Thai writes without spaces, so `make_cloze`'s word-boundary match can
    never fire and every Thai card fell back to a definition-only prompt —
    311 of 4,335 committed rows were usable, and 1,085 of the top 2,000 words
    had no sentence a card could show (CHECKS §29). Segmentation is the route
    the reading layer already takes; it was simply never wired to the cloze.

    A substring search is NOT the fix and would be worse than the fallback:
    `มาน` occurs inside `มานี่` (= มา + นี่), so the blank would land on half
    of two other words. The answer must come back as a segment of its own.

    The parse must also be CLEAN — every segment a known word. Greedy
    longest-match leaves unknown leftovers when it mis-carves a run, and
    those are exactly the cases where the headword "appears" by accident.
    Same stance as `thai_reading._segment`, which emits no reading at all
    rather than a partial one.
    """
    if not sentence or not answer:
        return None
    lexicon = cloze_lexicon()
    if not lexicon or answer not in lexicon:
        return None
    for run in _THAI_RUN.finditer(sentence):
        pieces = segment(run.group(), lexicon)
        if any(piece not in lexicon for piece in pieces):
            continue
        offset = run.start()
        for piece in pieces:
            if piece == answer:
                return offset, offset + len(piece)
            offset += len(piece)
    return None


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
