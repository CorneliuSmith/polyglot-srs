"""Drill-answerability validation, shared by the curriculum generator and the
contributor authoring tool.

A fill-in-the-blank drill is only usable if a learner can actually answer it:
the sentence must contain the {{answer}} blank, and the stored answer must
validate as CORRECT through the same NLP path the review screen uses. This
rejects unanswerable drills (missing blank, empty answer, or an answer the
language's NLP backend won't accept) before they ever reach a learner.
"""
from __future__ import annotations

from backend.services.nlp import validate_answer_async
from backend.services.nlp.base import AnswerResult

ANSWER_MARKER = "{{answer}}"


def has_blank(sentence: str | None) -> bool:
    return bool(sentence) and ANSWER_MARKER in sentence


async def is_answerable(language_code: str, answer: str | None) -> bool:
    """True if *answer* validates as CORRECT through the language's NLP backend."""
    answer = (answer or "").strip()
    if not answer:
        return False
    try:
        result, _ = await validate_answer_async(language_code, answer, answer)
    except ValueError:
        return False  # no NLP backend registered for this language
    return result == AnswerResult.CORRECT


async def validate_drill(language_code: str, sentence: str, answer: str) -> bool:
    """True if a drill has the blank and an answerable answer."""
    return has_blank(sentence) and await is_answerable(language_code, answer)
