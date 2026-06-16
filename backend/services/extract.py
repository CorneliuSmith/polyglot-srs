"""Pure text helpers for turning a learner's own text into study material.

No DB or NLP-registry access here — the router supplies the language's
normalize/lemmatize functions and the set of known words. Splitting and
tokenizing are intentionally simple and script-agnostic (works for Latin,
Cyrillic, Arabic, etc.).
"""
from __future__ import annotations

import re

ANSWER_MARKER = "{{answer}}"

# Sentence boundaries: ., !, ?, and the CJK/Arabic full stops, keeping it simple.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？؟])\s+")
# A "word" is a run of letters (any script), apostrophes, and combining marks.
_WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)


def split_sentences(text: str) -> list[str]:
    """Split text into trimmed, non-empty sentences."""
    parts = _SENTENCE_SPLIT.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def tokenize(sentence: str) -> list[str]:
    """Return the word tokens of a sentence, in order."""
    return _WORD.findall(sentence)


def make_cloze(sentence: str, answer: str) -> str | None:
    """Replace the first whole-word occurrence of *answer* with the blank.

    Case-insensitive match on the surface word. Returns None if the answer
    isn't a standalone word in the sentence.
    """
    answer = answer.strip()
    if not answer:
        return None
    pattern = re.compile(
        rf"(?<![^\W\d_]){re.escape(answer)}(?![^\W\d_])",
        re.IGNORECASE | re.UNICODE,
    )
    new, n = pattern.subn(ANSWER_MARKER, sentence, count=1)
    return new if n else None


def classify_words(
    tokens: list[str],
    known_words: set[str],
    normalize,
) -> list[dict]:
    """Mark each distinct token as known/new using normalized comparison.

    *known_words* is the set of already-known surface/normalized forms.
    Returns one entry per distinct token (first occurrence order).
    """
    seen: set[str] = set()
    out: list[dict] = []
    for token in tokens:
        norm = normalize(token)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append({"word": token, "normalized": norm, "known": norm in known_words})
    return out
