"""Placement grading helpers: synonym acceptance and level blending.

Two owner concerns, both about a placement that reads LOWER than the
learner actually is:

1. "I am worrying that you are just using vocab with synonyms being
   blocked." Correct, and it was worse than a nuisance. A vocabulary
   placement item shows an English definition and asks the learner to type
   the word; the only accepted answer is the seeded headword plus whatever
   sits in `vocabulary.alternatives` — and the shipped seeds populate that
   column for almost nothing. So "to walk" accepted *caminar* and graded
   *andar* a miss, and because the staircase steps DOWN on a miss, one
   blocked synonym could cost a whole band.

   `shares_a_sense` fixes the grading half: a typed word that is itself a
   real word of the course, whose English definition shares a WHOLE sense
   with the prompt's, is a correct answer to the question that was asked.

   Senses are compared whole, never word-by-word. "go" and "go on foot"
   are different senses; matching on the bare token "go" would accept
   *ir* for "to walk", which is the opposite failure.

2. The writing sample "is the best way to determine placement", so when a
   learner gives one it should decide their level — `blend_levels` lets
   production outrank the quiz, while clamping the move to a single band
   so one paragraph (or one generous judge) can't jump somebody two.
"""
from __future__ import annotations

import re

CEFR_ORDER = ("A1", "A2", "B1", "B2", "C1", "C2")

# Senses that carry no meaning on their own. A definition like "of; 's" must
# never make every function word a synonym of every other.
_EMPTY_SENSES = {
    "to", "the", "a", "an", "of", "be", "being", "is", "are", "it", "and",
    "or", "as", "at", "in", "on", "for", "with", "that", "this",
}
# Sense separators. English glosses in the seeds use semicolons between
# senses and commas within a list of near-equivalents ("big, large"); both
# are treated as sense boundaries, and a spelled-out " or " with them.
_SPLIT = re.compile(r"[;,/|]|\bor\b")
_PARENTHETICAL = re.compile(r"\([^)]*\)")
_NON_WORD = re.compile(r"[^\w\s'’-]", re.UNICODE)
_LEADING_ARTICLE = re.compile(r"^(?:to|the|a|an)\s+")
_WHITESPACE = re.compile(r"\s+")
# Shorter than this, a sense is too generic to prove synonymy on its own.
_MIN_SENSE_CHARS = 3


def senses(definition: str | None) -> set[str]:
    """The distinct meanings an English gloss lists, normalized.

    "to walk; to go on foot" → {"walk", "go on foot"}. Parentheticals are
    dropped (they gloss usage, not meaning), a leading article or infinitive
    "to" is stripped so "to walk" and "walk" are one sense, and senses that
    are bare function words are discarded.
    """
    out: set[str] = set()
    for part in _SPLIT.split((definition or "").lower()):
        part = _PARENTHETICAL.sub(" ", part)
        part = _NON_WORD.sub(" ", part)
        part = _WHITESPACE.sub(" ", part).strip()
        part = _LEADING_ARTICLE.sub("", part).strip()
        if len(part) < _MIN_SENSE_CHARS or part in _EMPTY_SENSES:
            continue
        out.add(part)
    return out


def shares_a_sense(prompt_definition: str | None,
                   candidate_definition: str | None) -> bool:
    """Whether a typed word's gloss answers the prompt's gloss.

    True only on a WHOLE shared sense — see the module docstring for why
    token overlap is the wrong test.
    """
    return bool(senses(prompt_definition) & senses(candidate_definition))


def blend_levels(quiz_level: str | None, writing_level: str | None) -> str | None:
    """The final placement from the two signals.

    The written sample wins where they disagree — it measures what the
    learner can BUILD, which is the thing a level is meant to describe —
    but only ever by one band. A short paragraph is a small piece of
    evidence: it can confirm that the quiz under-read someone, and it
    should not be able to move them from A2 to C1 on its own.
    """
    if writing_level not in CEFR_ORDER:
        return quiz_level
    if quiz_level not in CEFR_ORDER:
        return writing_level
    quiz_i = CEFR_ORDER.index(quiz_level)
    write_i = CEFR_ORDER.index(writing_level)
    clamped = max(quiz_i - 1, min(quiz_i + 1, write_i))
    return CEFR_ORDER[clamped]
